import os
import json

# This is the path to the key file we want to test
key_path = os.path.join("etl", "firebase-key.json")

print("--- STARTING DIAGNOSTIC SCRIPT ---")

# 1. Check if the file exists from Python's perspective
absolute_path = os.path.abspath(key_path)
print(f"Looking for file at absolute path: {absolute_path}")

if not os.path.exists(absolute_path):
    print("\nRESULT: FAILURE")
    print(">>> Python reports the file DOES NOT EXIST at this path. <<<")
    print("--- DIAGNOSTIC FINISHED ---")
    exit()

print("Python confirms the file exists.")

# 2. Try to read the file's content
print("\nAttempting to read file content...")
try:
    with open(absolute_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Successfully read the file.")

    # 3. Check if the content is empty
    if not content:
        print("\nRESULT: FAILURE")
        print(">>> The file was read successfully, but it is COMPLETELY EMPTY. <<<")
    else:
        print("The file is NOT empty.")

        # 4. Try to parse the content as JSON
        print("\nAttempting to parse content as JSON...")
        try:
            json.loads(content)
            print("\nRESULT: SUCCESS")
            print(">>> The file was read and successfully parsed as valid JSON. <<<")
        except json.JSONDecodeError as e:
            print("\nRESULT: FAILURE")
            print(f">>> FAILED to parse JSON. Error: {e} <<<")
            print("This means the file content is NOT valid JSON. It may have extra characters or be corrupt.")

except Exception as e:
    print("\nRESULT: FAILURE")
    print(f">>> An unexpected error occurred while reading the file: {e} <<<")

print("\n--- DIAGNOSTIC FINISHED ---")