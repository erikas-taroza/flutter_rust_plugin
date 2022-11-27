## Init Flutter plugin project
```
flutter create --template=plugin --platform=android,ios,linux,macos,windows --org com.pkgorg -a kotlin -i swift pkgname
```
Update **pubspec.yaml**:
```yaml
dependencies:
  # ...
  ffi: ^2.0.1
  flutter_rust_bridge: ^1.49.0
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
set(CRATE_NAME, "pkgname")
set(CRATE_NAME ${CRATE_NAME} PARENT_SCOPE)
add_subdirectory(${CRATE_NAME})
# ...
set(pkgname_bundled_libraries
    "$<TARGET_FILE:${CRATE_NAME}>"
    # ...
```
``linux/pkgname/CMakeLists.txt``:
```cmake
add_library(${CRATE_NAME} SHARED IMPORTED GLOBAL)
set_property(TARGET ${CRATE_NAME} PROPERTY IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/libpkgname.so")
```

### Init macOS
``macos/pkgname.podspec``:
```podspec
s.vendored_libraries = 'Libs/**/*'
```

### Init iOS
``ios/pkgname.podspec``:
```podspec
s.vendored_frameworks = 'Frameworks/**/*.xcframework'
# Or alternatively:
# s.vendored_libraries = 'Libs/**/*'
s.static_framework = true # This allows us to use the static library we built.
# I don't know what this does yet.
# If you have issues, you can try adding this.
# s.public_header_files = 'Classes/**/*.h'
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
    dummy_method_to_enforce_bundling()
}
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
    --rust-input rust/src/api.rs \
    --dart-output lib/src/bridge_generated.dart \
    --c-output ios/Classes/bridge_generated.h \
    --c-output macos/Runner/bridge_generated.h \
    --dart-decl-output lib/src/bridge_definitions.dart
```
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
Move the exported file to ``./linux/pkgname``

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
lipo "target/aarch64-apple-darwin/release/libpkgname.dylib" "target/x86_64-apple-darwin/release/libpkgname.dylib" -output "libpkgname.dylib" -create
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
