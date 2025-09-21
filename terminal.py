import os
import subprocess
import shutil
import re
from colorama import init, Fore, Style
import psutil
from collections import deque

# For command history and tab-completion on Windows
try:
    import pyreadline3 as readline
except ImportError:
    print("pyreadline3 not installed. Command history and tab-completion will not work.")

# Initialize colorama
init(autoreset=True)

# ---------- COMMAND HISTORY & AUTO-COMPLETION ----------
if 'readline' in globals():
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(' \t\n;')
    def complete(text, state):
        line = readline.get_line_buffer().split()
        if not line:
            return [c + os.sep for c in os.listdir('.')][state]
        else:
            matches = [f for f in os.listdir('.') if f.startswith(text)]
            if state < len(matches):
                return matches[state]
            else:
                return None
    readline.set_completer(complete)

# ---------- SESSION LOGGING ----------
LOG_FILE = "session.log"
def log_session(command, output):
    with open(LOG_FILE, "a") as f:
        f.write(f"> {command}\n{output}\n\n")

# ---------- UNDO/REDO STACKS ----------
undo_stack = deque(maxlen=20)
redo_stack = deque(maxlen=20)

# ---------- NLP PARSER WITH CONDITIONALS ----------
def parse_nlp(command):
    """
    Returns a list of tuples: (cmd, args, conditional)
    conditional can be None, "exists", "not_exists"
    """
    command = command.lower().strip()

    # Handle if-then-else
    if command.startswith("if "):
        m = re.match(r'if (.+?) then (.+?)(?: else (.+))?$', command)
        if m:
            condition, then_cmd, else_cmd = m.group(1), m.group(2), m.group(3)
            # Determine conditional
            cond_flag = None
            cond_flag_not = None
            if "exists" in condition:
                cond_flag = "exists"
            elif "not exists" in condition:
                cond_flag = "not_exists"
            # Execute based on condition
            if cond_flag == "exists":
                target = re.search(r'file (\S+)|folder (\S+)', condition)
                target_path = target.group(1) if target.group(1) else target.group(2)
                if os.path.exists(target_path):
                    return parse_nlp(then_cmd)
                elif else_cmd:
                    return parse_nlp(else_cmd)
            elif cond_flag == "not_exists":
                target = re.search(r'file (\S+)|folder (\S+)', condition)
                target_path = target.group(1) if target.group(1) else target.group(2)
                if not os.path.exists(target_path):
                    return parse_nlp(then_cmd)
                elif else_cmd:
                    return parse_nlp(else_cmd)
        # fallback
        return [(command, None, None)]

    # Split multi-step commands
    steps = re.split(r',| and ', command)
    parsed_steps = []

    for step in steps:
        step = step.strip()
        # Conditional exists/not exists inline
        conditional = None
        if " if it doesn't exist" in step:
            step = step.replace(" if it doesn't exist", "")
            conditional = "not_exists"
        elif " if exists" in step:
            step = step.replace(" if exists", "")
            conditional = "exists"

        # Commands
        if step.startswith("create folder") or step.startswith("make folder"):
            folder = step.split()[-1]
            parsed_steps.append(("mkdir", folder, conditional))
        elif step.startswith("delete folder") or step.startswith("delete file") or step.startswith("remove"):
            target = step.split()[-1]
            parsed_steps.append(("rm", target, conditional))
        elif step.startswith("move"):
            parts = step.split()
            if len(parts) >= 3:
                parsed_steps.append(("move", (parts[1], parts[2]), conditional))
        elif step.startswith("go to") or step.startswith("enter folder") or step.startswith("open folder"):
            parsed_steps.append(("cd", step.split()[-1], conditional))
        elif step in ["ls", "list files", "show files"]:
            parsed_steps.append(("ls", None, conditional))
        elif step in ["pwd", "current directory", "where am i"]:
            parsed_steps.append(("pwd", None, conditional))
        elif step == "undo":
            parsed_steps.append(("undo", None, None))
        elif step == "redo":
            parsed_steps.append(("redo", None, None))
        elif step == "cpu":
            parsed_steps.append(("cpu", None, None))
        elif step == "mem":
            parsed_steps.append(("mem", None, None))
        elif step == "ps":
            parsed_steps.append(("ps", None, None))
        else:
            parsed_steps.append((step, None, None))  # fallback

    return parsed_steps

# ---------- RUN COMMAND ----------
def run_command(cmd_tuple):
    cmd, args, conditional = cmd_tuple
    output = ""

    # Conditional checks
    if conditional == "not_exists":
        if cmd == "mkdir" and os.path.exists(args):
            print(Fore.YELLOW + f"Skipping mkdir '{args}' (already exists)")
            return
    elif conditional == "exists":
        if cmd in ["rm", "move"] and ((cmd == "rm" and not os.path.exists(args)) or (cmd == "move" and not os.path.exists(args[0]))):
            print(Fore.YELLOW + f"Skipping {cmd} (target does not exist)")
            return

    try:
        # ---------- BASIC COMMANDS ----------
        if cmd == "pwd":
            output = os.getcwd()
            print(Fore.CYAN + output)

        elif cmd == "cd":
            if args:
                try:
                    os.chdir(args)
                    output = f"Changed directory to {args}"
                    print(Fore.CYAN + output)
                except FileNotFoundError:
                    output = f"cd: no such file or directory: {args}"
                    print(Fore.RED + output)
            else:
                output = "cd: missing argument"
                print(Fore.YELLOW + output)

        elif cmd == "ls":
            items = os.listdir(os.getcwd())
            for item in items:
                if os.path.isdir(item):
                    print(Fore.BLUE + item + "/")
                else:
                    print(Fore.GREEN + item)
            output = "\n".join(items)

        elif cmd == "mkdir":
            if args:
                os.makedirs(args, exist_ok=True)
                undo_stack.append(("mkdir", args))
                redo_stack.clear()
                output = f"Folder '{args}' created."
                print(Fore.GREEN + output)
            else:
                output = "mkdir: missing folder name"
                print(Fore.YELLOW + output)

        elif cmd == "rm":
            if args:
                target = args
                if os.path.isdir(target):
                    shutil.rmtree(target)
                    undo_stack.append(("rm", target, "dir"))
                    redo_stack.clear()
                    output = f"Folder '{target}' removed."
                    print(Fore.RED + output)
                elif os.path.isfile(target):
                    shutil.move(target, target + ".bak")
                    undo_stack.append(("rm", target, "file"))
                    redo_stack.clear()
                    output = f"File '{target}' removed."
                    print(Fore.RED + output)
                else:
                    output = f"rm: cannot remove '{target}': No such file or directory"
                    print(Fore.RED + output)
            else:
                output = "rm: missing target name"
                print(Fore.YELLOW + output)

        elif cmd == "move":
            if len(args) == 2:
                src, dst = args
                if os.path.exists(src) and os.path.isdir(dst):
                    shutil.move(src, dst)
                    undo_stack.append(("move", src, dst))
                    redo_stack.clear()
                    output = f"Moved '{src}' → '{dst}/'"
                    print(Fore.GREEN + output)
                else:
                    output = "move: source or destination invalid"
                    print(Fore.RED + output)
            else:
                output = "move: syntax is move <file> <folder>"
                print(Fore.YELLOW + output)

        # ---------- SYSTEM MONITORING ----------
        elif cmd == "cpu":
            cpu_percent = psutil.cpu_percent(interval=1)
            output = f"CPU Usage: {cpu_percent}%"
            print(Fore.CYAN + output)

        elif cmd == "mem":
            mem = psutil.virtual_memory()
            output = f"Memory Usage: {mem.percent}% ({mem.used // (1024**2)}MB used / {mem.total // (1024**2)}MB total)"
            print(Fore.CYAN + output)

        elif cmd == "ps":
            output = "PID\tName"
            print(Fore.CYAN + output)
            for proc in psutil.process_iter(['pid', 'name']):
                line = f"{proc.info['pid']}\t{proc.info['name']}"
                print(Fore.WHITE + line)
                output += "\n" + line

        # ---------- UNDO/REDO ----------
        elif cmd == "undo":
            if undo_stack:
                action = undo_stack.pop()
                redo_stack.append(action)
                if action[0] == "mkdir":
                    shutil.rmtree(action[1])
                    output = f"Undo mkdir: removed folder '{action[1]}'"
                elif action[0] == "rm":
                    if action[2] == "dir":
                        os.makedirs(action[1], exist_ok=True)
                        output = f"Undo rm: restored folder '{action[1]}'"
                    elif action[2] == "file" and os.path.exists(action[1] + ".bak"):
                        shutil.move(action[1] + ".bak", action[1])
                        output = f"Undo rm: restored file '{action[1]}'"
                elif action[0] == "move":
                    shutil.move(os.path.join(action[2], os.path.basename(action[1])), os.getcwd())
                    output = f"Undo move: moved '{action[1]}' back to original location"
                print(Fore.YELLOW + output)
            else:
                output = "Nothing to undo"
                print(Fore.YELLOW + output)

        elif cmd == "redo":
            if redo_stack:
                action = redo_stack.pop()
                undo_stack.append(action)
                if action[0] == "mkdir":
                    os.makedirs(action[1], exist_ok=True)
                    output = f"Redo mkdir: recreated folder '{action[1]}'"
                elif action[0] == "rm":
                    if action[2] == "dir":
                        shutil.rmtree(action[1])
                        output = f"Redo rm: removed folder '{action[1]}'"
                    elif action[2] == "file":
                        os.remove(action[1])
                        output = f"Redo rm: removed file '{action[1]}'"
                elif action[0] == "move":
                    shutil.move(action[1], action[2])
                    output = f"Redo move: moved '{action[1]}' → '{action[2]}'"
                print(Fore.YELLOW + output)
            else:
                output = "Nothing to redo"
                print(Fore.YELLOW + output)

        # ---------- FALLBACK: RUN SYSTEM COMMAND ----------
        else:
            result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            if result.stdout:
                output = result.stdout.strip()
                print(Fore.WHITE + output)
            if result.stderr:
                output = result.stderr.strip()
                print(Fore.RED + output)

    except Exception as e:
        output = f"Error: {e}"
        print(Fore.RED + output)

    # Log session
    log_session(cmd, output)

# ---------- MAIN LOOP ----------
def main():
    print(Fore.MAGENTA + "Welcome to PyTerminal 🚀 (type 'exit' to quit)")
    while True:
        command = input(Fore.BLUE + f"{os.getcwd()} $ " + Style.RESET_ALL).strip()
        if command.lower() == "exit":
            print(Fore.MAGENTA + "Exiting PyTerminal... Goodbye 👋")
            break
        parsed_steps = parse_nlp(command)
        for step in parsed_steps:
            run_command(step)

if __name__ == "__main__":
    main()
