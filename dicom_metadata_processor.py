import os
import sys
import glob
import json
import datetime
import io
import pydicom
from pydicom.errors import InvalidDicomError
from pydicom.tag import Tag

PIXEL_DATA_TAG = Tag((0x7fe0, 0x0010))

def gather_dicom_metadata(filepath):
    """
    Gathers all metadata (except pixel data) from a single DICOM file using only pydicom.
    Returns a list of dictionaries, each representing a metadata entry.
    """
    metadata_entries = []

    try:
        ds = pydicom.dcmread(filepath, force=True)
    except InvalidDicomError:
        print(f"--- Skipping: {os.path.basename(filepath)} (Not a valid DICOM file or corrupted) ---", file=sys.stderr)
        return None
    except Exception as e:
        print(f"--- Error processing {os.path.basename(filepath)}: {e} ---", file=sys.stderr)
        return None

    for elem in ds:
        if elem.tag == PIXEL_DATA_TAG:
            continue

        keyword = elem.keyword if elem.keyword else pydicom.datadict.keyword_for_tag(elem.tag)
        if not keyword:
            if elem.tag.is_private:
                keyword = "Private Tag"
            else:
                keyword = "Unknown Standard Tag"

        value_to_store = elem.value

        if isinstance(value_to_store, bytes) and elem.VR in ['OB', 'OW', 'UN']:
            if len(value_to_store) > 1024 * 1024: # Example: if > 1MB, store a summary
                value_to_store = f"<Binary Data, length: {len(value_to_store)} bytes, first 16 hex: {value_to_store[:16].hex()}...>"

        entry = {
            "tag": elem.tag,
            "keyword": keyword,
            "value": value_to_store
        }
        metadata_entries.append(entry)

    return metadata_entries

def serialize_dicom_metadata(data, max_bytes_length=1024):
    """
    Safely serializes DICOM metadata to a JSON-compatible dictionary.

    Args:
        data (dict): The input dictionary with DICOM metadata.
        max_bytes_length (int): The maximum length for byte values.
                                If a byte value exceeds this, it will be replaced
                                with a placeholder string.

    Returns:
        dict: A new dictionary with values converted to JSON-friendly formats.
    """
    processed_data = {}
    for path, meta_list in data.items():
        processed_meta_list = []
        for item in meta_list:
            processed_item = item.copy()  # Create a copy to avoid modifying original data
            value = processed_item.get('value')

            if isinstance(value, bytes):
                if len(value) > max_bytes_length:
                    processed_item['value'] = f"<Binary data, {len(value)} bytes, removed>"
                else:
                    try:
                        processed_item['value'] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        processed_item['value'] = f"<Binary data, {len(value)} bytes, not UTF-8 decodable>"
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'Sequence':
                # Handle pydicom.Sequence objects
                processed_item['value'] = f"<Sequence, length {len(value)}>"
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'MultiValue':
                # Convert pydicom.multival.MultiValue to a list
                processed_item['value'] = list(value)
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'Tag':
                # Convert pydicom.tag.Tag to a string representation
                processed_item['value'] = str(value)
            elif isinstance(value, (list, dict)):
                # Ensure nested lists and dictionaries are handled recursively
                processed_item['value'] = _recursive_serialize(value, max_bytes_length)
            else:
                try:
                    # Attempt to convert other types to string if they are not directly JSON serializable
                    json.dumps(value)
                except TypeError:
                    processed_item['value'] = str(value)
            
            # Convert tuple tags to string representation (e.g., (0008, 0005) -> "(0008, 0005)")
            if 'tag' in processed_item and isinstance(processed_item['tag'], tuple):
                processed_item['tag'] = str(processed_item['tag'])

            processed_meta_list.append(processed_item)
        processed_data[path] = processed_meta_list
    return processed_data

def _recursive_serialize(obj, max_bytes_length):
    """Helper function for recursive serialization."""
    if isinstance(obj, dict):
        return {k: _recursive_serialize(v, max_bytes_length) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_recursive_serialize(elem, max_bytes_length) for elem in obj]
    elif isinstance(obj, bytes):
        if len(obj) > max_bytes_length:
            return f"<Binary data, {len(obj)} bytes, removed>"
        else:
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return f"<Binary data, {len(obj)} bytes, not UTF-8 decodable>"
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Sequence':
        return f"<Sequence, length {len(obj)}>"
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'MultiValue':
        return list(obj)
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Tag':
        return str(obj)
    else:
        try:
            json.dumps(obj) # Test if it's serializable
            return obj
        except TypeError:
            return str(obj)

def main():
    # Determine the base directory (where the script/executable is located)
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        base_directory = os.path.dirname(sys.executable)
        print(f"Running as an executable. Base directory: {base_directory}")
    else:
        # Running as a normal Python script
        base_directory = os.path.dirname(os.path.abspath(__file__))
        print(f"Running as a script. Base directory: {base_directory}")

    # Define output file paths
    output_filepath = os.path.join(base_directory, "dicom_metadata.json")
    log_output_file = os.path.join(base_directory, "dicom_processor_log.txt")

    # Redirect stdout to a log file
    original_stdout = sys.stdout
    log_file_handle = None
    try:
        log_file_handle = open(log_output_file, "w", encoding="utf-8")
        sys.stdout = log_file_handle

        print(f"Starting DICOM Metadata Processor - {datetime.datetime.now()}")
        print(f"Scanning for DICOM files in: {base_directory} (and subdirectories)")
        print(f"Metadata will be saved to: {output_filepath}")
        print(f"Logs will be saved to: {log_output_file}")
        print("-" * 50)

        all_dicom_files = []
        for ext in ['dcm', 'DCM', '']: # Common DICOM extensions or no extension
            search_pattern = os.path.join(base_directory, f"**/*.{ext}")
            all_dicom_files.extend(glob.glob(search_pattern, recursive=True))

        all_dicom_files = sorted(list(set(all_dicom_files)))

        if not all_dicom_files:
            print(f"No potential DICOM files found in '{base_directory}' or its subdirectories.")
            print("--- Processing Complete ---")
            return

        print(f"Found {len(all_dicom_files)} potential DICOM files. Processing...")
        print("-" * 50)

        collected_metadata = {} # Dictionary to store metadata, keys are file paths

        for i, filepath in enumerate(all_dicom_files):
            print_str = f"[{i+1}/{len(all_dicom_files)}] Processed file: {os.path.basename(filepath)}"
            metadata = gather_dicom_metadata(filepath)
            if metadata is not None:
                collected_metadata[filepath] = metadata
                print_str += f" -- {len(metadata)} meta fields"
            else:
                print_str += " -- No metadata"
            print(print_str)

        print("-" * 50)
        print(f"Finished processing {len(collected_metadata)} valid DICOM files.")
        
        json_processed_data = serialize_dicom_metadata(collected_metadata, max_bytes_length=1024)
        
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_processed_data, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved all metadata to: {output_filepath}")
        except Exception as e:
            print(f"Error saving metadata: {e}")

        print("\n--- DICOM processing complete ---")

    except Exception as e:
        print(f"\nAn unhandled error occurred during execution: {e}")
    finally:
        if log_file_handle:
            sys.stdout = original_stdout
            log_file_handle.close()
        print(f"Process finished. Check '{log_output_file}' for full logs and '{output_filepath}' for metadata.")

if __name__ == "__main__":
    main()
