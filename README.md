# Python-Based Command Terminal 🖥️⚡

A fully functional **Python-based terminal emulator** that mimics a real system terminal, with advanced features like **AI-powered command parsing**, **system monitoring**, **undo/redo**, **session logging**, and more.

---

## 🚀 Features

### 🔹 File & Directory Operations
- `pwd`, `cd`, `ls`, `mkdir`, `rm`, `move`
- Conditional execution (`if exists`, `if not exists`)
- Multi-step commands supported

### 🔹 System Monitoring
- `cpu` → Show CPU usage
- `mem` → Show memory usage
- `ps` → List active processes

### 🔹 AI / NLP Command Parsing
- Converts **natural language** instructions into system commands  
- Handles **multi-step** commands & conditions  

### 🔹 Undo / Redo
- Supports `undo` and `redo` for `mkdir`, `rm`, and `move` operations  

### 🔹 Command History & Tab-Completion
- Powered by **pyreadline3**  
- Use arrow keys for history navigation  
- Tab for auto-completion  

### 🔹 Session Logging
- Logs **all commands & outputs** to `session.log`

### 🔹 Clean & Color-Coded CLI
- Enhanced readability with **colorama**  

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/python-command-terminal.git
cd python-command-terminal

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
