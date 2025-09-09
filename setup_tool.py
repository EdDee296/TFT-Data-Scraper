#!/usr/bin/env python3
"""
TFT Stats Setup and Configuration Tool
Easily switch between local testing and production deployment
"""

import os
import configparser
import shutil


def modify_config(local_mode=True):
    """Modify configuration for local testing or production"""
    config_file = 'config.ini'

    if not os.path.exists(config_file):
        print("❌ config.ini not found. Run the main program first to create it.")
        return

    config = configparser.ConfigParser()
    config.read(config_file)

    if local_mode:
        # Local testing configuration
        config['api']['enable_remote_upload'] = 'False'
        config['debugging']['debug_mode'] = 'True'
        config['debugging']['backup_uploads'] = 'True'
        # More frequent for testing
        config['processing']['json_export_frequency'] = '2'
        config['processing']['regions'] = 'NA'  # Single region for testing

        mode_name = "Local Testing"
        print("🔧 Configured for LOCAL TESTING:")
        print("   ✅ Remote upload: DISABLED")
        print("   ✅ Debug mode: ENABLED")
        print("   ✅ Backup uploads: ENABLED")
        print("   ✅ Export frequency: Every 2 games")
        print("   ✅ Regions: NA only")

    else:
        # Production configuration
        config['api']['enable_remote_upload'] = 'True'
        config['debugging']['debug_mode'] = 'False'
        config['debugging']['backup_uploads'] = 'True'
        # Less frequent for production
        config['processing']['json_export_frequency'] = '5'
        config['processing']['regions'] = 'NA,EUW'  # Multiple regions

        mode_name = "Production"
        print("🚀 Configured for PRODUCTION:")
        print("   ✅ Remote upload: ENABLED")
        print("   ✅ Debug mode: DISABLED")
        print("   ✅ Backup uploads: ENABLED")
        print("   ✅ Export frequency: Every 5 games")
        print("   ✅ Regions: NA, EUW")

    # Save configuration
    with open(config_file, 'w') as f:
        config.write(f)

    print(f"\n💾 Configuration saved to {config_file}")
    print(f"🎯 Mode: {mode_name}")


def check_files():
    """Check what files are present"""
    print("📁 File Status Check:")
    print("=" * 40)

    files_to_check = [
        ('config.ini', 'Configuration file'),
        ('tft_stats_configurable.py', 'Main program (configurable)'),
        ('local_viewer.py', 'Local web viewer'),
        ('data.json', 'JSON data export'),
        ('tft.db', 'SQLite database'),
        ('ingame.png', 'Reference image: Game interface'),
        ('augments.png', 'Reference image: Augments panel'),
        ('select.png', 'Reference image: Player selector'),
        ('tftstats.pem', 'SSH key for remote upload')
    ]

    for filename, description in files_to_check:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename:<25} ({description}) - {size} bytes")
        else:
            print(f"❌ {filename:<25} ({description}) - Missing")

    print()

    # Check directories
    dirs_to_check = ['NeedsPlacement', 'Games', 'Augments', 'api_backups']
    print("📂 Directory Status:")
    for dirname in dirs_to_check:
        if os.path.exists(dirname):
            files_count = len(os.listdir(dirname))
            print(f"✅ {dirname}/ - {files_count} files")
        else:
            print(f"❌ {dirname}/ - Missing")


def create_backup():
    """Create a backup of current data"""
    import datetime

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'backup_{timestamp}'

    files_to_backup = ['tft.db', 'data.json', 'config.ini', 'runtime.log']

    os.makedirs(backup_dir, exist_ok=True)

    backed_up = []
    for filename in files_to_backup:
        if os.path.exists(filename):
            shutil.copy(filename, backup_dir)
            backed_up.append(filename)

    if backed_up:
        print(f"💾 Backup created in {backup_dir}/")
        print(f"   Files backed up: {', '.join(backed_up)}")
    else:
        print("⚠️  No files to backup found")
        os.rmdir(backup_dir)


def view_current_config():
    """Display current configuration"""
    config_file = 'config.ini'

    if not os.path.exists(config_file):
        print("❌ config.ini not found")
        return

    config = configparser.ConfigParser()
    config.read(config_file)

    print("⚙️  Current Configuration:")
    print("=" * 40)

    for section_name in config.sections():
        print(f"\n[{section_name}]")
        for key, value in config[section_name].items():
            print(f"  {key} = {value}")


def main():
    print("=== TFT Stats Configuration Tool ===\n")

    while True:
        print("Choose an option:")
        print("1. 🧪 Configure for LOCAL TESTING")
        print("2. 🚀 Configure for PRODUCTION")
        print("3. 📁 Check file status")
        print("4. ⚙️  View current configuration")
        print("5. 💾 Create backup")
        print("6. 🌐 Start local web viewer")
        print("7. ❌ Exit")
        print()

        choice = input("Enter choice (1-7): ").strip()

        if choice == '1':
            modify_config(local_mode=True)
            print("\n🧪 Ready for local testing!")
            print("   Run: python main.py")
            print("   View: python local_viewer.py")

        elif choice == '2':
            modify_config(local_mode=False)
            print("\n🚀 Ready for production!")
            print("   Make sure tftstats.pem SSH key is present")
            print("   Run: python main.py")

        elif choice == '3':
            check_files()

        elif choice == '4':
            view_current_config()

        elif choice == '5':
            create_backup()

        elif choice == '6':
            print("🌐 Starting local web viewer...")
            print("   This will open your browser automatically")
            print("   Press Ctrl+C to stop the server")
            try:
                os.system('python local_viewer.py')
            except KeyboardInterrupt:
                print("\n⏹️  Viewer stopped")

        elif choice == '7':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please try again.")

        print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    main()
