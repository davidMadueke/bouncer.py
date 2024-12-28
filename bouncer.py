# Import dependencies
import configparser
from configparser import ConfigParser
import os
import io
import re
import sys
import shutil
from enum import Enum
import time
from pydub import AudioSegment
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Declare Variable Constants
CONFIGFILE_NAME = "config.ini"
SCRIPT_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
SOURCE_DIR = os.path.dirname(SCRIPT_DIR)
CONSOLIDATE_PATH = "Samples/Processed/Consolidate"
RECORDINGS_PATH = "Samples/Recorded"

DEFAULT_useSourceDirName = True
DEFAULT_sampleRate = 44100

DEFAULT_CONFIG_MODEL = {
    'Metadata': {
        'version': '0',
        'songID': '',
        'Current Date of Version':  str(datetime.today().strftime('%d-%m-%Y')),
        'Sample Rate': ''
    },
    'Song Details': {
        'Song Name': '',
        'Artist': '',
        'BPM': '',
        'Key': '',
        'Time Signature': '',
        'Duration': 'N/A',
        'Genre Abbreviation': ''
    },
    'Options': {
        'useSourceDirNames': 'false',
        'saveMasterEditions': 'false',
        'abletonAsDAW': 'true',
        'abletonConsolidateFlag': 'true'
    },
    'Directories': {
        'showcaseDir': '',
        'sourceDir': '',
        'alpDir': '',
        'stemsDir': '',
    }
}
class StemTypes(Enum):
    MASTER = "MASTER PRINT"
    EFFECTS = "EFFECTS PRINT"
    DRUMS = "DRUMS PRINT"
    KEYS = "KEYS PRINT"
    ORCHESTRAL = "ORCHESTRAL PRINT"
    BASS = "BASS PRINT"
    FX = "FX PRINT"
    GUITAR = "GUITAR PRINT"
    VOCALS = "VOCALS PRINT"
    SYNTHS = "SYNTHS PRINT"
    SAMPLE = "SAMPLE PRINT"

# Select the current Directory using TKinter and add that to the config.ini file
def select_directory(directoryName: str = "ALP"):
    """Open a dialog for the user to select a directory and return its filepath."""
    # Create a hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Open a directory selection dialog
    print(f"Please select the {directoryName} Directory using the file explorer popup ")
    selected_dir = filedialog.askdirectory(title=f"Select the {directoryName} Directory")

    # If a directory is selected, print it; otherwise, indicate no selection
    if selected_dir:
        print(f"Selected Directory as {directoryName} folder: {selected_dir}")
        return selected_dir
    else:
        print("No directory selected. Please Rerun the script to try again")
        EXIT = input("Press Enter to exit script")
        raise SystemExit(1)

# Extract from source directory name key information
def parse_sourceDirName(source_dir_path):
    """
    Extracts song details from the source directory name in the format:
    "SongID" "[Song Artist - Song Name]" "Song BPM"BPM "Song Key"
    """
    # Regex expression to match the pattern
    name = os.path.basename(source_dir_path)

    # Original pattern r'(\w+)\s+\[(.*?)\s*-\s*(.*?)\]\s+(\d+)BPM\s+(\w+)'
    pattern = r'(\d{8})_(\d+)_([A-Z]+)\s+\[([A-Z\s]+)\s*-\s*([A-Z\s]+)\]\s+(\d+)\s*BPM\s+([a-zA-Z]+)([A-Z\s]+)'
    match = re.match(pattern, name)

    if not match:
        print(f"Source Directory '{name}' does not match the expected pattern.\nSongID [Song Artist - Song Name] Song BPM Song Key")
        print("Generating default config.ini file")
        # prompt user to select showcaseDir
        new_showcase_dir = select_directory('Showcase')
        # Create the defualt config.ini file with all values (except ones above) defaulted to blank
        config = configparser.ConfigParser()
        for section, options in DEFAULT_CONFIG_MODEL.items():
            config.add_section(section)
            for key, value in options.items():
                config.set(section, key, str(value))

        # Set the default showcase directory to the user selected one
        config.set("Directories", "showcaseDir", str(new_showcase_dir))
        config_path = os.path.join(source_dir_path, CONFIGFILE_NAME)
        # Change
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        print(
            f"Default config.ini file has been created at {config_path}.")
        return False

    print("Source Directory name matches expected pattern. Extracting Song Details")
    # Extracting the groups
    date = match.group(1)
    day_id = match.group(2)
    genre_abbreviation = match.group(3)
    song_id= f"{date}_{day_id}_{genre_abbreviation}"

    artist = match.group(4)
    song_name = match.group(5)
    bpm = match.group(6)
    key = match.group(7) + match.group(8)

    # Create the configuration file as it doesn't exist yet
    print("Creating config file")
    cfgfile = open(os.path.join(source_dir_path, CONFIGFILE_NAME), "w")

    # Add content to the file
    Config = configparser.ConfigParser()
    Config.add_section("Metadata")
    Config.set("Metadata", "Version", str(0))
    Config.set("Metadata", "SongID", song_id)
    Config.set("Metadata", "Current Date of Version", str(datetime.today().strftime('%d-%m-%Y')))
    Config.set("Metadata", "Sample Rate", str(DEFAULT_sampleRate))

    Config.add_section("Song Details")
    # Make sure Artists and Song Name is formatted correctly to account for use of Commas
    Config.set("Song Details", "Artist", re.sub(r'[,\\/*?:"<>|]', '_', artist))
    Config.set("Song Details", "Song Name", re.sub(r'[,\\/*?:"<>|]', '_', song_name))
    Config.set("Song Details", "Time Signature", re.sub(r'[,\\/*?:"<>|]', '_', "4/4"))
    Config.set("Song Details", "BPM", bpm)
    Config.set("Song Details", "Key", key)
    Config.set("Song Details", "Duration", "N/A")
    Config.set("Song Details", "Genre Abbreviation", genre_abbreviation)

    Config.add_section("Directories")
    new_showcase_dir = select_directory("Showcase")
    Config.set("Directories", "showcaseDir", str(new_showcase_dir))

    Config.write(cfgfile)
    print(f"Song Details extracted from Source Directory name have been saved to {CONFIGFILE_NAME}")
    cfgfile.close()
    return True

def createSongID(source_dir, genre_abbreviation: str = " "):
    """Generate a valid songID based on the source directory's creation date.
    Note that dayID (of the form 01) denotes the unique identifier given to seperate projects in the projects directory that were created on the same day

    Args:
        source_dir (str): Path to the source directory.
        genre_abbreviation (str): Abbreviation for the genre.

    Returns:
        str: A unique songID of the form 'DDMMYYYY_dayID-[Genre Abbreviation]'.
    """
    # Create a ConfigParser object
    config = configparser.ConfigParser()
    ini_filepath = os.path.join(source_dir, CONFIGFILE_NAME)

    if not os.path.exists(ini_filepath):
        raise FileNotFoundError(f"The file {CONFIGFILE_NAME} does not exist.")

    config.read_file(open(ini_filepath))

    # Check if 'Song Details' section exists (it should, as per the original script)
    if 'Song Details' not in config:
        raise KeyError(f"No 'Song Details' section found in {CONFIGFILE_NAME}.")

    # Get the creation time of the directory
    creation_time = os.path.getctime(source_dir)
    creation_date = datetime.fromtimestamp(creation_time).strftime("%d%m%Y")

    # List directories in the parent folder
    parent_dir = os.path.dirname(source_dir)
    all_dirs = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))]

    # Filter directories created on the same day
    day_count = 0
    for d in all_dirs:
        dir_path = os.path.join(parent_dir, d)
        dir_creation_time = os.path.getctime(dir_path)
        dir_creation_date = datetime.fromtimestamp(dir_creation_time).strftime("%d%m%Y")
        if dir_creation_date == creation_date:
            day_count += 1
        if dir_path == source_dir:
            break

    # Generate dayID
    day_id = f"{day_count:02}"

    # Combine to create songID
    song_id = f"{creation_date}_{day_id}_[{genre_abbreviation}]"
    config["Metadata"]["songID"] = song_id

    # Write the updated config back to the file
    with open(ini_filepath, 'w') as configfile:
        config.write(configfile)
    print(f"Song Id updated to {song_id} in {CONFIGFILE_NAME}")
    return song_id


# Create a helper function that appends one to the config file
def increment_version(source_dir):
    """
    Increments the version number in the provided .ini file.
    If the Version field doesn't exist, it initializes it to 1.
    """
    # Create a ConfigParser object
    config = configparser.ConfigParser()
    ini_filepath = os.path.join(source_dir, CONFIGFILE_NAME)

    # Read the .ini file
    if not os.path.exists(ini_filepath):
        raise FileNotFoundError(f"The file {CONFIGFILE_NAME} does not exist.")

    config.read_file(open(ini_filepath))

    # Check if 'Song Details' section exists (it should, as per the original script)
    if 'Song Details' not in config:
        raise KeyError(f"No 'Song Details' section found in {CONFIGFILE_NAME}.")

    # Get the current version, or set it to 0 if it doesn't exist
    current_version = config['Metadata'].getint('Version', fallback=0)

    # Increment the version
    new_version = current_version + 1
    config['Metadata']['Version'] = str(new_version)

    # Write the updated config back to the file
    with open(ini_filepath, 'w') as configfile:
        config.write(configfile)

    print(f"Version updated to Version {new_version} in {CONFIGFILE_NAME}")

# Helper function to get the latest print of the particular stems
def get_latest_stems_print(directory, stems_print: str = "MASTER PRINT",
                           consolidate_sel: bool = True, alp_dir_flag: bool = False):
    """
    Finds the latest .wav file in the Ableton Live Project (ALP) directory or Stems Directory that starts with the string stems_print.
    Returns the full file path of the latest file.
    """
    # List all files in the directory, if consolidate chosen, then files taken from the consolidate path else the recorded paths is chosen
    if alp_dir_flag:
        if consolidate_sel:
            consolidate_folder = os.path.join(directory, CONSOLIDATE_PATH)
        else:
            consolidate_folder = os.path.join(directory, RECORDINGS_PATH)
    else:
        consolidate_folder = directory

    files = [f for f in os.listdir(consolidate_folder) if f.startswith(stems_print) and f.endswith('.wav')]


    if not files:
        con_record_print_string = "consolidate" if consolidate_sel else "recorded"
        print(f"No files found starting with '{stems_print}' in {con_record_print_string} folder of Ableton Live Project Directory.\n")
        return None

    # Full file paths
    full_paths = [os.path.join(consolidate_folder, f) for f in files]

    # Get the latest file by creation date (for Linux use `os.stat(f).st_mtime` for modification time)
    latest_file = max(full_paths, key=os.path.getmtime)

    print(f"The latest {stems_print} file: {os.path.basename(latest_file)}")
    return latest_file


# Copy the Master Track as an mp3 into a new Song Showcase Directories Folder
# Check the version number of the project and append that to the name of the copied master
# If a previous version of the master is found in the Bounced Directories, replace it with this version
def copy_Master_to_ShowcaseDir(master_file, showcase_dir, source_dir,
                               song_id, artist, song_name, bpm, key,
                               non_standard_time_signature_flag: bool):
    # Ensure the destination directory exists
    if not os.path.exists(showcase_dir):
        os.makedirs(showcase_dir)
    # Remove any previous version of the audio file in the destination directory if found depending on whether the saveMasterEditions flag is selected.
    for file_name in os.listdir(showcase_dir):
        if song_id in file_name and artist in file_name and song_name in file_name:
            prev_version_path = os.path.join(showcase_dir, file_name)
            os.remove(prev_version_path)
            print(f"Removed previous version: {os.path.basename(prev_version_path)}")

    ini_filepath = os.path.join(source_dir, CONFIGFILE_NAME)
    Config = configparser.ConfigParser()
    Config.read_file(open(ini_filepath))

    if 'Metadata' not in Config:
        raise KeyError(f"No 'Metadata' section found in {CONFIGFILE_NAME}.")

    if master_file is None:
        print("\nCould not copy Master Track to Showcase Directory. Stopping Bouncer process \n")
        EXIT = input("Press Enter to exit script")
        raise(SystemExit(1))

    # Construct the new filename
    version = Config['Metadata']['Version']
    time_signature = (f"{Config['Song Details']['Time Signature']}"
           if non_standard_time_signature_flag else "")
    new_filename = f'{song_id} v{version} [{artist} - {song_name}] {bpm} {time_signature} {key}.mp3'
    print(f"Adding latest master to showcase directory: {new_filename}")

    master_track = AudioSegment.from_file(master_file, format="wav")

    file_handle = master_track.export(os.path.join(showcase_dir, new_filename),
                               format="mp3",
                               bitrate="192k",
                               tags={"artist": song_name})
    print(f"Added latest version: {os.path.basename(os.path.join(showcase_dir, new_filename))}")

# Helper function to create a new entry in the release notes directory
def create_release_note(source_dir, config_filename=CONFIGFILE_NAME,
                        non_standard_time_signature: bool =False):
    # Initialising configParser file and creating release notes directory if not already created

    ini_filepath = os.path.join(source_dir, config_filename)
    Config = configparser.ConfigParser()
    Config.read_file(open(ini_filepath))

    if 'Song Details' not in Config:
        raise KeyError(f"No 'Song Details' section found in {config_filename}.")
    if 'Metadata' not in Config:
        raise KeyError(f"No 'Metadata' section found in {config_filename}.")

    release_notes_dir = os.path.join(source_dir, "release_notes")
    if not os.path.exists(release_notes_dir):
        os.makedirs(release_notes_dir)

    # Based on config file we create a new txt file with a file name of form v Version + date
    release_note_filename = f"Release Notes v{Config['Metadata']['Version']} {Config['Metadata']['Current Date of Version']}.txt"

    release_note_filepath = os.path.join(release_notes_dir, release_note_filename)
    # Create the content for the file
    file_content = (
        f"Song Details:\n"
        f"Date of Version: {Config['Metadata']['Current Date of Version']}\n"
        f"Artist: {Config['Song Details']['Artist']}\n"
        f"Song Name: {Config['Song Details']['Song Name']}\n"
        f"Genre Abbreviation: {Config['Song Details']['Genre Abbreviation']}\n"
        f"BPM: {Config['Song Details']['BPM']}\n"
        f"Song Duration in Seconds: {Config['Song Details']['Duration']}\n"
        f"Sample Rate in Hertz: {Config['Metadata']['Sample Rate']}\n"
        f"Key Signature: {Config['Song Details']['Key']}\n"
        + (f"Time Signature: {Config['Song Details']['Time Signature']}\n"
           if non_standard_time_signature else "")
        + f"Comments: \n"
    )

    # Write the content to the text file
    with open(release_note_filepath, 'w') as file:
        file.write(file_content)

    print(f"Song details saved to {os.path.basename(release_note_filepath)}")
    return release_note_filepath

# Helper function that creates a POST directory to store the version based deliverables folders that will be sent to clients
def generate_POST(source_dir, directory, release_note_filepath,
                  config_filename=CONFIGFILE_NAME, stem_types: StemTypes = StemTypes,
                  consolidate_sel: bool = True, alp_dir_flag: bool = False):
    # Initialising configParser file and creating release notes directory if not already created
    ini_filepath = os.path.join(source_dir, config_filename)
    Config = configparser.ConfigParser()
    Config.read_file(open(ini_filepath))

    if 'Song Details' not in Config:
        raise KeyError(f"No 'Song Details' section found in {config_filename}.")
    if 'Metadata' not in Config:
        raise KeyError(f"No 'Metadata' section found in {config_filename}.")

    posts_dir = os.path.join(source_dir, "POST")
    if not os.path.exists(posts_dir):
        os.makedirs(posts_dir)

    # Within the POST dir, there will be sub folders housing each post
    song_name = Config['Song Details']['Song Name']
    song_artist = Config['Song Details']['Artist']
    post_dir = os.path.join(posts_dir, f"[{song_artist}-{song_name}] v{Config['Metadata']['Version']} {Config['Metadata']['Current Date of Version']}")

    if not os.path.exists(post_dir):
        os.makedirs(post_dir)
    # Helper function to create collect all of the necessary stems for the project into the stems folder
    def collect_stems(parent_dir, directory, StemType: StemTypes,
                      cons_sel: bool=consolidate_sel, sd_flag:bool=alp_dir_flag):
        # Create new STEMS subfolder if one hasn't been created
        stems_dir = os.path.join(parent_dir, "STEMS")
        if not os.path.exists(stems_dir):
            os.makedirs(stems_dir)

        # Search through the ALP directory for the latest editions of each stem
        # Copy each stem into this STEMS directory
        for type in (StemType):
            stem_path = get_latest_stems_print(directory, consolidate_sel=cons_sel,
                                               alp_dir_flag = sd_flag, stems_print=type.value)
            # Construct the new filename
            if stem_path is not None:
                new_filename = f'{type.value}.mp3'

                stem_track = AudioSegment.from_file(stem_path, format="wav")

                file_handle = stem_track.export(os.path.join(stems_dir, new_filename),
                                              format="mp3",
                                              bitrate="192k")

                print(f"Exported {new_filename} into STEMS folder\n")

    # perform the collect stems function
    collect_stems(parent_dir=post_dir, directory=directory, StemType=stem_types)

    # Copy the release note into the POST entry
    release_note_filename = f"Release Notes v{Config['Metadata']['Version']} {Config['Metadata']['Current Date of Version']}"
    post_release_note_filepath = os.path.join(post_dir, release_note_filename)
    print(f"\nCopied {release_note_filename} into POST folder")
    shutil.copy2(release_note_filepath, post_release_note_filepath)

    print(f"POST entry for v{Config['Metadata']['Version']} dated {Config['Metadata']['Current Date of Version']} has been created")


def create_default_config(config_path, source_dir_path):
    # check default_useSourceDirName
    if DEFAULT_useSourceDirName:
        # If default_useSourceDirName is true then run parse_sourceDirNam
        parse_sourceDirName_flag = parse_sourceDirName(source_dir_path)
        increment_version(source_dir_path)
        if not parse_sourceDirName_flag:
            createSongID(source_dir_path,genre_abbreviation= ' ')
        print(
            f"config.ini file has been created at {config_path}.\n Please fill out the rest of the file and rerun the script.")
        return
    # prompt user to select showcaseDir
    new_showcase_dir = select_directory('Showcase')

    # Create the defualt config.ini file with all values (except ones above) defaulted to blank
    config = configparser.ConfigParser()
    for section, options in DEFAULT_CONFIG_MODEL.items():
        config.add_section(section)
        for key, value in options.items():
            config.set(section, key, str(value))

    # Set the default showcase directory to the user selected one
    config.set("Directories", "showcaseDir", str(new_showcase_dir))
    # Change
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print(f"Default config.ini file has been created at {config_path}.\n Please fill out the rest of the file and rerun the script.")
    return
def add_missing_keys(config, defaults, config_path):
    """Add missing keys to the config file based on the defaults."""
    missing_values = False
    print("Checking that all fields are in config.ini")
    for section, keys in defaults.items():
        if section not in config:
            config.add_section(section)
            missing_values = True
        for key, value in keys.items():
            if key not in config[section]:
                #config[section][key] = value
                config.set(section, key, value)
                missing_values = True


    if missing_values:
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        print("Missing keys were added to config.ini. Please fill out the empty ones.")

    return missing_values

def check_config(config_path, defaults: dict = DEFAULT_CONFIG_MODEL):
    """Check if config file exists, create it if not, and prompt user to fill it out."""
    if not os.path.exists(config_path):
        create_default_config(config_path)
        return False  # Config file created, but needs user input

    # Load config and add missing keys if any
    config = configparser.ConfigParser()
    config.read(config_path)

    #if add_missing_keys(config, defaults, config_path):
    #    return False  # Missing keys were added, user needs to fill them out

    # Check for empty values
    missing_values = False
    for section in config.sections():
        for key in config[section]:
            if not config[section][key] and (not section == "Directories"):
                print(f"The configuration entry '{key}' in section '[{section}]' is empty. Please fill it out.")
                missing_values = True
    missing_fields = add_missing_keys(config, defaults, config_path)
    if missing_values or missing_fields:
        print("Please update the config.ini file with the required values and rerun the script.")
        return False  # Config file needs user input

    return True  # Config file is ready to use

def main(source_dir: str = SOURCE_DIR):
    if not os.path.exists(source_dir):
        print("The source directory doesn't exist")
        raise SystemExit(1)
    # Check if a config.ini file exists
    ini_filepath = os.path.join(source_dir, CONFIGFILE_NAME)
    if not os.path.exists(ini_filepath):
        # If it doesn't then run create_default_config()
        create_default_config(ini_filepath, source_dir_path=source_dir)
        return

    # Use the config file, check if useSourceDirName is used and check if the abletonAsDAW flag is asserted high
    config = configparser.ConfigParser()
    ini_filepath = os.path.join(source_dir, CONFIGFILE_NAME)
    config.read_file(open(ini_filepath))

    # Run the final checks before proceeding with the main algorithm
    if not check_config(ini_filepath):
        return  # Exit if config is incomplete

    if config["Options"].getboolean("useSourceDirName"):
        parse_sourceDirName_flag = parse_sourceDirName(source_dir_path)
        increment_version(source_dir_path)
        if not parse_sourceDirName_flag:
            createSongID(source_dir_path, genre_abbreviation=' ')
        print(
            f"config.ini file has been edited at {config_path}.\n Please fill out the rest of the file and rerun the script.")
        return

    if config["Options"].getboolean("abletonAsDAW"):
        # If it is then check if the ALP_Dir does not exist or it is not valid
        if not os.path.isdir(config["Directories"]["alpDir"]) :
            # If this condition is satisfied then prompt user to select ALP_DIR
            new_alp_dir = select_directory()
            config.set("Directories", "alpDir", str(new_alp_dir))
        config.set("Directories", "stemsDir", 'N/A')
        # If it isnt asserted high, then prompt user to select Stems_Dir
    else:
        # If it isnt asserted high then create a stems_dir entry in config.ini and make alp_dir blank
        if not os.path.isdir(config["Directories"]["stemsDir"]):
            # If this condition is satisfied then prompt user to select stems_DIR
            new_stems_dir = select_directory('Stems')
            config.set("Directories", "stemsDir", str(new_stems_dir))
        config.set("Directories", "alpDir", 'N/A')

    if not os.path.isdir(config["Directories"]["showcaseDir"]):
        # If this condition is satisfied then prompt user to select stems_DIR
        new_showcase_dir = select_directory('Showcase')
        config.set("Directories", "showcaseDir", str(new_showcase_dir))
    config.set("Directories", "sourceDir", source_dir)


    ##### The MAIN ALGORITHM ######
    alp_dir: str = config["Directories"]["alpDir"]
    stems_dir: str = config["Directories"]["stemsDir"]
    source_dir: str = config["Directories"]["sourceDir"]
    showcase_dir: str = config["Directories"]["showcaseDir"]
    version: str = config["Metadata"]["version"]

    save_master_editions_flag: bool = config["Options"].getboolean("saveMasterEditions")
    ableton_as_daw_flag: bool = config["Options"].getboolean("abletonAsDAW")
    # The abletonConsolidateFlag is used to choose whether to get the stems from the recorded folder or the consolidate folder
    ableton_consolidate_sel_flag: bool = config["Options"].getboolean("abletonConsolidateFlag")

    song_id = config["Metadata"]["songID"]
    ( artist, song_name, time_signature, bpm, key,
      duration, genre_abbreviation) = config["Song Details"].values()

    # Make sure Artists and Song Name and Time Signature is formatted correctly to account for use of Commas
    config.set("Song Details", "Artist", re.sub(r'[,\\/*?:"<>|]', '_', artist))
    config.set("Song Details", "Song Name", re.sub(r'[,\\/*?:"<>|]', '_', song_name))
    config.set("Song Details", "Time Signature", re.sub(r'[,\\/*?:"<>|]', '_', time_signature))

    with open(ini_filepath, 'w') as configfile:
        #print("Changes have been made to config.ini")
        config.write(configfile)

    # A simple Helper function to make sure that
    def timeSignatureNot4_4(time_signature):
        return True if not (time_signature == "4_4") else False

    phasesCount: int = 1 # For the CLI to count each phase

    print(f"\nPhase {phasesCount}: Copy Latest Master Track to Showcase Directory")
    phasesCount += 1
    directory = alp_dir if ableton_as_daw_flag else stems_dir
    master_track = get_latest_stems_print(directory,
                                          stems_print="MASTER PRINT",
                                          consolidate_sel=ableton_consolidate_sel_flag,
                                          alp_dir_flag=ableton_as_daw_flag)
    copy_Master_to_ShowcaseDir(master_track, showcase_dir, source_dir,
                               song_id, artist, song_name, bpm, key,
                               non_standard_time_signature_flag=timeSignatureNot4_4(time_signature))

    print(f"\nPhase {phasesCount}: Create a release note for version {version} and save it in the release notes directory")
    phasesCount += 1
    release_note_filepath = create_release_note(source_dir, config_filename=CONFIGFILE_NAME,
                                                non_standard_time_signature=timeSignatureNot4_4(time_signature))

    print(f"\nPhase {phasesCount}: Create a new post entry in the POST directory and copy over the stems and release note into this entry")
    phasesCount += 1
    generate_POST(source_dir, alp_dir, release_note_filepath,
                  config_filename=CONFIGFILE_NAME,
                  consolidate_sel= ableton_consolidate_sel_flag,
                  alp_dir_flag= ableton_as_daw_flag,
                  stem_types=StemTypes)
    # Add one to the version number and save it to config file
    increment_version(source_dir)
    return

if __name__ == "__main__":
    main()
    EXIT = input("Press Enter to exit script")