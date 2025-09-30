import subprocess

bash_file = "bash.sh"  # replace with full path if needed

try:
    # Run bash script
    subprocess.run(["bash", bash_file], check=True)
    print(f"{bash_file} executed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error running {bash_file}: {e}")
