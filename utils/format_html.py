import os
import shutil

# Path to the html_files directory
html_files_path = "html_files/"

# Iterate over all items in the html_files directory
for item in os.listdir(html_files_path):
    item_path = os.path.join(html_files_path, item)

    # Check if the item is a directory
    if os.path.isdir(item_path):
        # Construct the new file name by removing the trailing underscore
        new_file_name = item[:-6] + item[-5:]

        # Path to the index.html inside the directory
        index_html_path = os.path.join(item_path, "index.html")

        # Check if the index.html file exists
        if os.path.exists(index_html_path):
            # New path for the renamed html file in the html_files directory
            new_html_path = os.path.join(html_files_path, new_file_name)

            # Move and rename the index.html file
            shutil.move(index_html_path, new_html_path)
            print(f"Moved and renamed: {index_html_path} -> {new_html_path}")
        else:
            print(f"No index.html found in {item_path}")

        # Remove the original directory
        shutil.rmtree(item_path)
        print(f"Removed directory: {item_path}")