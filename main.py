import sys
import traceback
import importlib

# 3 sources
SCRIPTS = [
    "google_search_handler",
    "youtube_handler",
    "n8n_forum_handler"
]

def run_script(script_name):
    #Load and run a script to populate n8n workflow popularity data from a specific source
    try:
        module = importlib.import_module(script_name)
        print(f"\n=== Running {script_name} ===")
        result = module.main()
        print(f"{script_name} completed. Inserted {len(result)} records.\n")
    except Exception as e:
        print(f"Error in {script_name}: {e}")
        traceback.print_exc()
        sys.exit(1)

def main():
    # Main Entry Point
    for script in SCRIPTS:
        run_script(script)
    print("\nAll scripts completed successfully.")

if __name__ == "__main__":
    main()
