## Init Flutter plugin project
```
flutter create --template=plugin --platform=android,ios,linux,macos,windows --org com.pkgorg -a kotlin -i swift pkgname
```
Update **pubspec.yaml**:
```yaml
dependencies:
  # ...
  ffi: ^2.0.1
  flutter_rust_bridge: ^1.65.0
# ...
dev_dependencies:
  # ...
  ffigen: ^6.1.2
```

## Write Rust impl
```
cargo new pkgname --lib
```
- Add to a folder in root dir of plugin project.
- Update Cargo.toml:
```toml
[lib]
crate-type = ["staticlib", "cdylib"]
```

### Init Android
``android/build.gradle``:
```gradle
sourceSets {
    // ...
    main.jniLibs.srcDirs = ['src/main/jniLibs']
}
```

### Init Linux
``linux/CMakeLists.txt`` at the bottom:
```cmake
set(pkgname_bundled_libraries
    "${CMAKE_CURRENT_SOURCE_DIR}/libpkgname.so"
    # ...
```

### Init macOS
``macos/pkgname.podspec``:
```podspec
s.vendored_libraries = 'Libs/**/*'
```

**IMPORTANT:** XCode strips the code from the library so you need to make sure it bundles.

``macos/Classes/SwiftpkgnamePlugin.swift``
```swift
public static func register(with registrar: FlutterPluginRegistrar) {
    // ...
    let _ = dummy()
}

public static func dummy() -> Int64
{ return dummy_method_to_enforce_bundling() }
```

### Init iOS
``ios/pkgname.podspec``:
```podspec
s.vendored_frameworks = 'Frameworks/**/*.xcframework'
s.static_framework = true # This allows us to use the static library we built.
```

**IMPORTANT:** XCode strips the code from the library so you need to make sure it bundles.

Objective-C: ``ios/Classes/pkgnamePlugin.m``
```objc
...
#import "../Classes/bridge_generated.h"
...
@implementation pkgnamePlugin
+ (void)registerWithRegistrar:(NSObject<FlutterPluginRegistrar>*)registrar {
  dummy_method_to_enforce_bundling(); // <--- Insert this to prevent stripping.
  [SwiftpkgnamePlugin registerWithRegistrar:registrar];
}
@end
```

Swift: ``ios/Classes/SwiftpkgnamePlugin.swift``
```swift
public static func register(with registrar: FlutterPluginRegistrar) {
    // ...
    let _ = dummy()
}

public static func dummy() -> Int64
{ return dummy_method_to_enforce_bundling() }
```

### Init Windows
``windows/CMakeLists.txt``:
```cmake
set(pkgname_bundled_libraries
    "${CMAKE_CURRENT_SOURCE_DIR}/pkgname.dll"
    # ...
```

## Flutter->Rust Codegen
```
flutter_rust_bridge_codegen \
    --rust-input ./rust/src/lib.rs \
    --dart-output ./lib/src/bridge_generated.dart \
    --dart-decl-output ./lib/src/bridge_definitions.dart \
    --c-output ./rust/src/bridge_generated.h
```
- Copy and move `./rust/src/bridge_generated.h` to `./macos/Classes` and `./ios/Classes`
- Fix any errors.
- Move everything in the folder to a subfolder called ``src``
- Add [this file](https://raw.githubusercontent.com/Desdaemon/flutter_rust_bridge_template/main/lib/ffi.dart) to lib/src
- Create API for users.

**NOTE:** If codegen fails with incorrect signatures, try this:
```sh 
export CPATH="$(clang -v 2>&1 | grep "Selected GCC installation" | rev | cut -d' ' -f1 | rev)/include"
```

## Export Android Libs
```
rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
```
```
cargo install cargo-ndk
```
```
cargo ndk -t arm64-v8a -t armeabi-v7a -t x86 -t x86_64 -o ../android/src/main/jniLibs build --release
```

## Export Linux Lib
```
rustup target add x86_64-unknown-linux-gnu
```
```
cargo build --release --target x86_64-unknown-linux-gnu
```
Move the exported file to ``./linux``

## Export macOS Libs
```
rustup target add aarch64-apple-darwin x86_64-apple-darwin
```
```
cargo build --release --target aarch64-apple-darwin
```
```
cargo build --release --target x86_64-apple-darwin
```
```
lipo "target/aarch64-apple-darwin/release/libpkgname.a" "target/x86_64-apple-darwin/release/libpkgname.a" -output "libpkgname.a" -create
```
Move the exported file to ``./macos/Libs``

## Export iOS Libs
```
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios
```
```
cargo build --release --target aarch64-apple-ios
```
```
cargo build --release --target aarch64-apple-ios-sim
```
```
cargo build --release --target x86_64-apple-ios
```
```
lipo "target/aarch64-apple-ios-sim/release/libpkgname.a" "target/x86_64-apple-ios/release/libpkgname.a" -output "libpkgname.a" -create
```
```
xcodebuild -create-xcframework -library ./target/aarch64-apple-ios/release/libpkgname.a -library ./libpkgname.a -output pkgname.xcframework
```
Move the framework to ``./ios/Frameworks``

## Export Windows Libs
```
rustup target add x86_64-pc-windows-msvc
```
```
cargo build --release --target x86_64-pc-windows-msvc
```
Move the exported file to ``./windows``

## Updating the project
- Run code gen above.
- Export all libs again.

## Publish to pub.dev
pub.dev does not allow projects to be over 100MB. This means you cannot include the libraries when publishing.
To fix this, you can use the tutorial [here](https://cjycode.com/flutter_rust_bridge/library/platform_setup.html).

However, I took slightly different steps to make it more simple. In the following code,
replace the names in the GitHub URLs accordingly.

### Android
- Add CMakeLists.txt to `./android`.
- Edit `build.gradle`.

`CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.10)

# Download the binaries from GitHub.
# The version of the release from GitHub.
set(Version "1.0.0")
set(LibPath "${CMAKE_CURRENT_SOURCE_DIR}/src/main/jniLibs")

if(NOT EXISTS "${LibPath}/arm64-v8a/libpkgname.so")
  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/android/src/main/jniLibs/arm64-v8a/libpkgname.so?raw=true"
    "${LibPath}/arm64-v8a/libpkgname.so"
    TLS_VERIFY ON
  )

  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/android/src/main/jniLibs/armeabi-v7a/libpkgname.so?raw=true"
    "${LibPath}/armeabi-v7a/libpkgname.so"
    TLS_VERIFY ON
  )

  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/android/src/main/jniLibs/x86/libpkgname.so?raw=true"
    "${LibPath}/x86/libpkgname.so"
    TLS_VERIFY ON
  )

  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/android/src/main/jniLibs/x86_64/libpkgname.so?raw=true"
    "${LibPath}/x86_64/libpkgname.so"
    TLS_VERIFY ON
  )
endif()
```

`build.gradle`:
```gradle
android {
    // ...
    externalNativeBuild {
        cmake {
            path "CMakeLists.txt"
        }
    }
}
```

### Linux
Add this to `linux/CMakeLists.txt`:
```cmake
# Download the binary from GitHub.
set(Version "1.0.0")
set(LibPath "${CMAKE_CURRENT_SOURCE_DIR}/libpkgname.so")
if(NOT EXISTS ${LibPath})
  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/linux/libpkgname.so?raw=true"
    ${LibPath}
    TLS_VERIFY ON
  )
endif()
```

### macOS
Add this to `macos/pkgname.podspec`:
```podspec
# Download the binary from GitHub.
version = "1.0.0"
lib_url = "https://github.com/username/pkgname/blob/v#{version}/macos/Libs/libpkgname.a?raw=true"

`
mkdir Libs
cd Libs
if [ ! -f libpkgname.a ]
then
  curl -L "#{lib_url}" -o libpkgname.a
fi
cd ..
`
```

### iOS
Add this to `ios/pkgname.podspec`:
```podspec
# Download the binaries from GitHub.
version = "1.0.0"
lib_url = "https://github.com/username/pkgname/blob/v#{version}/ios/Frameworks/pkgname.xcframework"

`
mkdir Frameworks
cd Frameworks
if [ ! -d pkgname.xcframework ]
then
  mkdir pkgname.xcframework
  cd pkgname.xcframework
  mkdir ios-arm64
  mkdir ios-arm64_x86_64-simulator
  curl -L "#{lib_url}/Info.plist?raw=true" -o Info.plist
  curl -L "#{lib_url}/ios-arm64/libpkgname.a?raw=true" -o ios-arm64/libpkgname.a
  curl -L "#{lib_url}/ios-arm64_x86_64-simulator/libpkgname.a?raw=true" -o ios-arm64_x86_64-simulator/libpkgname.a
fi
cd ../..
`
```

### Windows
Add this to `windows/CMakeLists.txt`:
```cmake
# Download the binary from GitHub.
set(Version "1.0.0")
set(LibPath "${CMAKE_CURRENT_SOURCE_DIR}/pkgname.dll")
if(NOT EXISTS ${LibPath})
  file(DOWNLOAD
    "https://github.com/username/pkgname/blob/v${Version}/windows/pkgname.dll?raw=true"
    ${LibPath}
    TLS_VERIFY ON
  )
endif()
```

## Notes
Here are issues that I ran into, with solutions that may help you:

### OpenSSL
I had trouble building this dependency on a few platforms.

In your ``Cargo.toml``, add an ``openssl-sys`` dependency with the ``vendored`` feature.

- **Linux:** Install ``Perl`` and ``Perl CPAN``
- **Windows:** Install ``Strawberry Perl``
- **iOS:** The ``vendored`` feature does not work on the ``aarch64-apple-ios-sim`` target, so you need to use these environment variables when building. The ``OPENSSL_INCLUDE_DIR`` points to the ``include`` folder in the ``openssl`` source, so update this to wherever you cloned it.
  - OPENSSL_STATIC=1
  - OPENSSL_LIB_DIR=/usr/local/lib
  - OPENSSL_INCLUDE_DIR=~/Downloads/openssl/include
  - OPENSSL_NO_VENDOR=1

Clone [openssl](https://github.com/openssl/openssl) and run the ``Configure`` script.

### iOS Missing Symbols
In my project, I had a Rust dependency to Apple's coreaudio API. When I tried to build the Flutter app,
it would always give me multiple missing symbol errors. I was able to fix this by adding a framework
to the example app's Runner project. Make sure the framework is not being embeded.
![image](https://user-images.githubusercontent.com/68450090/203773185-a44b7c83-ed10-4a65-969c-41a7e21f537a.png)

## Examples
If you are unsure of how something is implemented, feel free to checkout my project [simple_audio](https://github.com/erikas-taroza/simple_audio).