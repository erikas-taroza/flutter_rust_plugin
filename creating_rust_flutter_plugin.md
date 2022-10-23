## Init Flutter plugin project
``flutter create --template=plugin --platform=android,ios,linux,macos,windows --org com.erikas -a kotlin -i swift pkgname``

## Write Rust impl
``cargo new pkgname --lib``
- Add to a folder in root dir of plugin project.
- Update Cargo.toml:
```toml
[lib]
crate-type = ["staticlib", "cdylib"]
```

### Init Android
android -> build.gradle:
```gradle
sourceSets {
    ...
    main {
        jniLibs.srcDirs = ['src/main/jniLibs']
    }
}
```

### Init Linux
linux -> CMakeLists.txt at the bottom:
```cmake
set(CRATE_NAME, "pkgname")
set(CRATE_NAME ${CRATE_NAME} PARENT_SCOPE)
add_subdirectory(${CRATE_NAME})
# ...
set(pkgname_bundled_libraries
    "$<TARGET_FILE:${CRATE_NAME}>"
    ...
```

### Init macOS and iOS
macos/ios -> pkgname.podspec:
```podspec
s.vendored_libraries = 'Libs/**/*'
```

### Init Windows
windows -> CMakeLists.txt:
```cmake
set(pkgname_bundled_libraries
    "${CMAKE_CURRENT_SOURCE_DIR}/pkgname.dll"
    ...
```

## Flutter->Rust Codegen
```
flutter_rust_bridge_codegen \
    --rust-input native/src/api.rs \
    --dart-output lib/bridge_generated.dart \
    --c-output ios/Runner/bridge_generated.h \
    --c-output macos/Runner/bridge_generated.h
```
- Fix any errors.
- Create API for users.

## Export Android Libs
```
rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
cargo install cargo-ndk
cargo ndk -t arm64-v8a -t armeabi-v7a -t x86 -t x86_64 -o ./android/src/main/jniLibs
```

## Export Linux Lib
```
rustup target add x86_64-unknown-linux-gnu
cargo build --release --target x86_64-unknown-linux-gnu
Move the exported file to ./linux/pkgname
```

## Export macOS Libs
```
rustup target add aarch64-apple-darwin x86_64-apple-darwin
cargo build --release --target aarch64-apple-darwin
cargo build --release --target x86_64-apple-darwin
lipo "target/aarch64-apple-darwin/release/pkgname.dylib" "target/x86_64-apple-darwin/release/pkgname.dylib" -output "pkgname.dylib" -create
```
Move the exported file to ./macos/Libs

## Export iOS Libs
```
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios
cargo build --release --target aarch64-apple-ios
cargo build --release --target aarch64-apple-ios-sim
cargo build --release --target x86_64-apple-ios
lipo "target/aarch64-apple-ios-sim/release/pkgname.a" "target/x86_64-apple-ios/release/pkgname.a" -output "pkgname.a" -create
```
Move the export file to ./ios/Libs

## Export Windows Libs
```
rustup target add x86_64-pc-windows-msvc
cargo build --release --target x86_64-pc-windows-msvc
```
Move the exported file to ./windows

## Updating the project
- Run code gen above.
- Export all libs again.
