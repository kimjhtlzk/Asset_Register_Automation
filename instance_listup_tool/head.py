import subprocess
import time

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


def main():
    start_time = time.time()

    print()
    print(f"1. {ORANGE}[AWS]{RESET}")
    print(f"2. {GREEN}[TENCENT]{RESET}")
    print(f"3. {YELLOW}[GCP]{RESET}")
    print(f"4. {BLUE}[Azure] (not support it yet){RESET}")

    print()
    choice = input("Choose CSP (Enter number or name): ")

    if choice == '1' or choice.lower() == 'aws':
        subprocess.run(['python', 'aws_instance_listup_tool.py'])
    elif choice == '2' or choice.lower() == 'tencent':
        subprocess.run(['python', 'tencent_instance_listup_tool.py'])
    elif choice == '3' or choice.lower() == 'gcp':
        subprocess.run(['python', 'gcp_instance_listup_tool.py'])
    elif choice == '4' or choice.lower() == 'azure':
        subprocess.run(['python', 'azure_instance_listup_tool.py'])
    else:
        print("Invalid choice. Please enter a valid number or name.")

    elapsed_time = time.time() - start_time
    hours, remainder = divmod(int(elapsed_time), 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\n{BLUE}logic running: {hours}h : {minutes}m : {seconds}s{RESET}\n")


if __name__ == "__main__":
    main()
