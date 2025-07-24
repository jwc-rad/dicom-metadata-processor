# DICOM Metadata Processor

This repository contains a single Python script, `dicom_metadata_processor.py`, designed to extract and save metadata from DICOM files.

## 📄 What it Does

The `dicom_metadata_processor.py` script performs the following actions:

1.  **Scans for DICOM files**: It automatically discovers all DICOM files (`.dcm`, `.DCM`, or files with no extension that are valid DICOMs) present in the same directory as the script and within all its subdirectories.
2.  **Extracts Metadata**: For each identified DICOM file, it extracts all available metadata tags using the `pydicom` library, excluding the large pixel data to keep the output concise.
3.  **Saves Output**:
    * **JSON File**: All collected metadata is compiled into a single JSON file named `dicom_metadata.json` in the same directory where the script is run (or the executable is located). The metadata is structured with file paths as keys and a list of tag-keyword-value dictionaries as values.
    * **Log File**: A detailed log of the processing, including file scanning, errors, and progress, is saved to `dicom_processor_log.txt` in the same directory.

## 🚀 How to Use

### Running the Python Script

To run the script directly, you need to have Python and `pydicom` installed.

1.  **Install `pydicom`**:
    ```bash
    pip install pydicom
    ```
2.  **Place the script**: Put `dicom_metadata_processor.py` into the directory where your DICOM files are located, or into a directory that contains subdirectories with your DICOM files.
3.  **Execute the script**:
    ```bash
    python dicom_metadata_processor.py
    ```

### Creating an Executable for Other Operating Systems (e.g., Windows)

You can use `PyInstaller` to create a standalone executable that can be run without installing Python or `pydicom` on the target machine.

1.  **Install `PyInstaller`**:
    ```bash
    pip install pyinstaller
    ```
2.  **Generate the executable**: Navigate to the directory containing `dicom_metadata_processor.py` in your terminal and run:
    ```bash
    pyinstaller --onefile dicom_metadata_processor.py
    ```
    This command will create a `dist` folder, and inside it, you'll find the executable (e.g., `dicom_metadata_processor.exe` on Windows, or just `dicom_metadata_processor` on Linux/macOS).

### Using the Executable

Once you have the executable file:

1.  **Copy the executable**: Simply copy the `dicom_metadata_processor` (or `dicom_metadata_processor.exe`) file to any directory containing DICOM files or subdirectories with DICOM files that you wish to process.
2.  **Run the executable**: Double-click the executable (on Windows) or run it from the terminal (on Linux/macOS).
    The script will automatically detect the current directory as its base and scan for DICOM files within it and its subdirectories.
3.  **Retrieve Output**: Upon completion, `dicom_metadata.json` (containing the extracted metadata) and `dicom_processor_log.txt` (containing the processing logs) will be saved in the *same directory* where the executable was run.
