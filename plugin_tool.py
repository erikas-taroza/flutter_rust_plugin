import argparse, re, os, shutil, requests, sys

parser = argparse.ArgumentParser(
    usage="Put this file in your root project directory and execute the commands.",
    description="A tool to help you with initializing and building a Flutter plugin with Rust."
)

parser.add_argument(
    "-i", "--init",
    action="store_true",
    help="Initialize the Flutter plugin project for development with Rust."
)

parser.add_argument(
    "-c", "--code-gen",
    action="store_true",
    help="Generates the FFI bridge using flutter_rust_bridge."
)

parser.add_argument(
    "-b", "--build",
    action="store_true",
    help="Builds the Rust code. This will have to be run on Linux, Windows, and macOS if you want to target all platforms."
)

def init():
    print("Initializing your project...")

    package_name = ""

    # Add dependencies to pubspec.yaml.
    print("Adding dependencies to pubspec.yaml...")

    pubspec_text = open("./pubspec.yaml", "r").read()
    
    with open("./pubspec.yaml", "w") as pubspec:
        package_name = pubspec_text.split("name: ")[1].split("\n")[0].strip()

        def add_dependency(dependency:str, version:str = "", dev:bool = False) -> str:
            key = ("dev_" if dev else "") + "dependencies"
            split:list[str] = re.split(rf"\s{key}:\s", pubspec_text)
            lines:list[str] = split[1].split("\n")
            
            for i in range(0, len(lines)):
                if lines[i].isspace() or len(lines[i]) == 0:
                    break

            lines.insert(i, f"  {dependency}: {version}")

            return split[0] + f"\n{key}:\n" + "\n".join(lines)

        if "ffi:" not in pubspec_text:
            pubspec_text = add_dependency("ffi", version="^2.0.1", dev=False)

        if "flutter_rust_bridge:" not in pubspec_text:
            pubspec_text = add_dependency("flutter_rust_bridge", version="^1.50.0", dev=False)
        
        if "ffigen:" not in pubspec_text:
            pubspec_text = add_dependency("ffigen", version="^6.1.2", dev=True)

        pubspec.write(pubspec_text)

    # Start the Rust project.
    print(f"Creating the Rust project with the name \"{package_name}\"...")
    
    os.makedirs("rust", exist_ok=True)
    path = f"./rust/{package_name}"
    os.system(f"cargo new {path} --lib")

    for item in os.listdir(path):
        shutil.move(f"{path}/{item}", f"./rust")

    os.rmdir(path)

    toml_text = open("./rust/Cargo.toml", "r").read()
    with open("./rust/Cargo.toml", "w") as toml:
        split = toml_text.split("\n\n")
        toml_text = split[0] + '\n\n[lib]\ncrate-type = ["staticlib", "cdylib"]\n\n' + "\n".join(split[1:])
        toml.write(toml_text)

    # Initialize the Flutter platform specific things.
    print("Initializing platform specific project files...\n")
    #TODO


def code_gen():
    print("Generating code with flutter_rust_bridge...\n")

    os.system("cargo install flutter_rust_bridge_codegen")
    os.system('CPATH="$(clang -v 2>&1 | grep "Selected GCC installation" | rev | cut -d\' \' -f1 | rev)/include" \
        flutter_rust_bridge_codegen \
        --rust-input ./rust/src/lib.rs \
        --dart-output ./lib/src/bridge_generated.dart \
        --dart-decl-output ./lib/src/bridge_definitions.dart \
        --c-output ./ios/Classes/bridge_generated.h \
        --c-output ./macos/Classes/bridge_generated.h')

    if "ffi.dart" not in os.listdir("./lib/src"):
        package_name = open("./rust/Cargo.toml", "r").read().split("name = \"")[1].split("\"")[0]
        pascal_case_package_name = package_name.lower().replace("_", " ").title().replace(" ", "")

        file = open("./lib/src/ffi.dart", "w")
        file.write(
            requests.get(r"https://raw.githubusercontent.com/Desdaemon/flutter_rust_bridge_template/main/lib/ffi.dart")
                .text
                .replace("native", package_name)
                .replace("Native", pascal_case_package_name)
        )


def build():
    print("Building Rust code...\n")

    package_name = open("./rust/Cargo.toml", "r").read().split("name = \"")[1].split("\"")[0]
    is_linux = sys.platform == "linux"
    is_windows = sys.platform == "win32"
    is_mac = sys.platform == "darwin"

    if is_linux or is_windows or is_mac:
        print("Building Android libraries...\n")

        os.system("rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android")
        os.system("cargo install cargo-ndk")
        os.system("cd rust && cargo ndk -t arm64-v8a -t armeabi-v7a -t x86 -t x86_64 -o ../android/src/main/jniLibs build --release && cd ..")

    if is_linux:
        print("Building Linux libraries...\n")

        os.system("rustup target add x86_64-unknown-linux-gnu")
        os.system("cd rust && cargo build --release --target x86_64-unknown-linux-gnu && cd ..")
        shutil.move(f"./rust/target/x86_64-unknown-linux-gnu/release/{package_name}.so", f"./linux/{package_name}")

    if is_windows:
        print("Building Windows libraries...\n")

        os.system("rustup target add x86_64-pc-windows-msvc")
        os.system("cd rust && cargo build --release --target x86_64-pc-windows-msvc && cd ..")
        shutil.move(f"./rust/target/x86_64-pc-windows-msvc/release/{package_name}.dll", "./windows")

    if is_mac:
        print("Building macOS libraries...\n")

        # Build for macOS.
        os.system("rustup target add aarch64-apple-darwin x86_64-apple-darwin")
        os.system("cd rust")
        os.system("cargo build --release --target aarch64-apple-darwin")
        os.system("cargo build --release --target x86_64-apple-darwin")
        os.system(f'lipo "./target/aarch64-apple-darwin/release/lib{package_name}.dylib" "target/x86_64-apple-darwin/release/lib{package_name}.dylib" -output "lib{package_name}.dylib" -create')
        os.system("cd ..")
        shutil.move(f"./rust/lib{package_name}.dylib", "./macos/Libs")

        # Build for iOS
        print("Building iOS libraries...\n")

        os.system("rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios")
        os.system("cd rust")
        os.system("cargo build --release --target aarch64-apple-ios")
        os.system("cargo build --release --target aarch64-apple-ios-sim")
        os.system("cargo build --release --target x86_64-apple-ios")
        os.system(f'lipo "target/aarch64-apple-ios-sim/release/lib{package_name}.a" "target/x86_64-apple-ios/release/lib{package_name}.a" -output "lib{package_name}.a" -create')
        os.system(f"xcodebuild -create-xcframework -library ./target/aarch64-apple-ios/release/lib{package_name}.a -library ./lib{package_name}.a -output {package_name}.xcframework")
        os.remove(f"./{package_name}.a")
        os.system("cd ..")
        shutil.move(f"./rust/{package_name}.xcframework", "./ios/Frameworks")

    return

if __name__ == "__main__":
    args = parser.parse_args()

    if args.init:
        init()
        print("\n")

    if args.code_gen:
        code_gen()
        print("\n")

    if args.build:
        build()
        print("\n")