<h1>
  <img src="geniustmusicplayer/images/icon.png" alt="GeniusT Music Player logo" width="200" align="center"/>
  GeniusT Music Player
</h1>

![GitHub release (latest by
date)](https://img.shields.io/github/v/release/allerter/geniustmusicplayer)

GeniusT Music Player is an Android music player that plays recommended songs (or at least their previews).

Table of Contents
-----------------

> -   [Introduction](#introduction)
> -   [Build](#build)
> -   [Missing Features/issues](#missing-featuresissues)

## Introduction
This music player uses the recommender at the [GeniusT](https://github.com/allerter/geniust#geniust-shuffle) repo to get you playlists based on your preferences and play them on Android. You can use the packages APK in the bin folder to run it on an Android device. The APK can run on API >= 21 (Android 5) and higher. It's also compiled for the `armeabi-v7a` architecture, but that shouldn't be a problem on almost all devices. 

The app doesn't play full songs, only their previews. The app used to be able to download full songs and eventually playing full songs would be an option, but I decided to remove it.

## Build
You can read the guide below or check out the [GitHub Action](https://github.com/allerter/geniustmusicplayer/blob/main/.github/workflows/python-app.yml) that builds the APK on every push.
To build the app, you need to run my python-for-android fork for three reasons:
 - The Most important of them is that AndroidX is enabled on it (at the time of writing this, upstream P4A doesn't have it).
 - `PythonActivity.java` has been edited to extend the splash screen to 30s (it's manually removed in the app once the UI is loaded)
 - `AndroidManifest.tmpl.xml` has been edited to add activities for the OAuth logins.

Install the [P4A dependencies](https://python-for-android.readthedocs.io/en/latest/quickstart/#installing-dependencies) and then install my P4A fork.
```bash
# Feel free to use a higher Cython version if it works
pip install Cython==0.29.22
pip install git+https://github.com/Allerter/python-for-android.git
```
Then fork this repo:
```bash
git clone https://github.com/allerter/geniustmusicplayer ~/geniustmusicplayer
cd ~/geniustmusicplayer
```
Now you can run the following command to compile the APK. Just replace `--ndk_dir` with your NDK path. P4A usually recommends `ndk-r19c` for the SDK and you'll need the one for API 30. Although you can just change the `--android_api` and compile for any API >= 21 that you want.
```bash
export ANDROID_API_LEVEL=30
export ARCH=armeabi-v7a
export SDK_DIR={my_sdk_dir}
export NDK_DIR={my_ndk_dir}
```
Build command:
```bash
p4a apk \
    --enable-androidx \
    --arch $ARCH \
    --ndk_dir $NDK_DIR \
    --android_api $ANDROID_API_LEVEL \
    --bootstrap sdl2 \
    --dist_name geniustmusicplayer \
    --name="GeniusT Music Player" \
    --version 0.8 \
    --package org.allerter.geniustmusicplayer \
    --requirements python3,kivy==2.0.0,https://github.com/kivymd/KivyMD/archive/c792038.zip,android,sdl2_ttf==2.0.15,requests,urllib3,idna,chardet,oscpy,pillow \
    --orientation portrait \
    --window \
    --private ~/geniustmusicplayer/geniustmusicplayer \
    --permission INTERNET \
    --permission ACCESS_NETWORK_STATE \
    --permission FOREGROUND_SERVICE \
    --service gtplayer:~/geniustmusicplayer/service.py \
    --depend "com.android.support:support-compat:28.0.0" \
    --depend "androidx.legacy:legacy-support-v4:1.0.0" \
    --depend "com.google.code.gson:gson:2.8.5" \
    --presplash-lottie ~/geniustmusicplayer/geniustmusicplayer/images/presplash.json \
    --presplash-color white \
    --icon ~/geniustmusicplayer/geniustmusicplayer/images/icon.png \
    --add-aar ~/geniustmusicplayer/geniustmusicplayer/spotify-auth-release-1.2.3.aar \
    --add-aar ~/geniustmusicplayer/geniustmusicplayer/genius-auth-release-1.2.4.aar \
    --intent-filters ~/geniustmusicplayer/geniustmusicplayer/intent_filters.xml
```
Note: The Spotify auth AAR is from the [Spotify Authentication Library](https://github.com/spotify/android-auth), but Genius has no such library right now. So I removed some things from the Spotify's source code, renamed everything from `spotify` to `genius` while preserving case and then compiled it.


## Missing Features/Issues
- Playing songs on loop
- Canceling retries for requests after 3 consecutive failures. Right now the app will infinitely retry to make network requests.
- Changing playlist length. Currently all new playlists only have 5 songs.
- Making the app respond to notification controls. The app shows a notification with media controls, but the media controls do nothing.
Currently the app will just display a toast saying that `Spotify isn't installed on this device`.
- Skipping playlists. Users can skip songs, but to skip playlists they need to skip to last song and then skip once more to get a new playlist.
- Sharing songs. Adding a button to share songs which shares the song's artist, title and Spotify link as a text.
- Linking to Spotify correctly. According to Spotify [design guidelines](https://developer.spotify.com/documentation/general/design-and-branding/), if an app links to Spotify and Spotify's app isn't installed, the link should open in a WebView or the browser.
