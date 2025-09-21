import streamlit as st
import subprocess
import os

st.set_page_config(page_title="Python Command Terminal", layout="wide")
st.title("🖥️ Python-Based Command Terminal")

# Keep command history
if "history" not in st.session_state:
    st.session_state.history = []

# Input box
command = st.text_input("Enter Command:")

# Run command on submit
if st.button("Run"):
    if command.strip():
        try:
            # Run the command in subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout if result.stdout else result.stderr
        except Exception as e:
            output = str(e)
        
        # Save in history
        st.session_state.history.append((command, output))

# Show command history
st.subheader("📜 Command History")
for cmd, out in st.session_state.history[::-1]:
    st.markdown(f"**> {cmd}**")
    st.code(out, language="bash")
