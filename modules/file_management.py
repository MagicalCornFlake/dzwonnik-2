"""
Functionality for reading the .env files in the program root directory.
"""
import os


def read_env_files() -> bool:
    return_value = False
    for filename in os.listdir():
        if not filename.endswith('.env'):
            continue
        env_name = filename.rstrip('.env')
        if env_name in os.environ:
            print(f"\nEnvironment variable '{env_name}' is already set, ignoring the .env file.")
            continue
        else:
            print("\nGlobal environment variable not found. Setting it in the program's local memory.")
            # for var in os.environ:
            #     print(var)
        return_value = True
        with open(filename, 'r') as file:
            env_value = file.read()
            os.environ[env_name] = env_value
            print(f"Set environment variable value '{env_name}' to '{env_value}'.")
    # Newline for readability
    print()
    return return_value
