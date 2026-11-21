# Trivandrum Pork POS – Android source project

This is a native Android app project built with Kotlin + Jetpack Compose. It stores menu items and sales locally on the device using Android SharedPreferences (JSON). It does not connect to WordPress.

## Build an installable APK
1. Install Android Studio on a computer (Windows, macOS or Linux).
2. Extract this ZIP.
3. In Android Studio choose **Open** and select the `TrivandrumPorkPOS-Android` folder.
4. Allow Gradle sync and install any requested Android SDK (compile SDK 35).
5. Connect an Android phone with USB debugging enabled, or use an emulator.
6. Choose **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
7. Android Studio creates the debug APK at:
   `app/build/outputs/apk/debug/app-debug.apk`
8. Transfer that APK to your Android phone, open it, and allow installation from that source when Android asks.

## Notes
- Package: `com.trivandrumpork.pos`
- Minimum Android: 8.0 (API 26)
- Offline POS: menu, cart, customer details and bill history are stored locally.
- WhatsApp: uses an Android share/open link (`wa.me`) with a prefilled text message. Staff must press Send in WhatsApp.
- This ZIP is Android source code, **not a prebuilt APK**. This environment does not have Android SDK/Gradle build tools, so no installable APK has been compiled or tested here.
- Before live use, test backup/recovery and validate totals and bill workflow on your device.
