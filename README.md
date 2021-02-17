# geniustmusicplayer
GeniusT Music Player plays you recommended songs (or at least their previews).

## Build
CLI command:
`
p4a apk --enable-androidx --sdk_dir=/home/hazhir/.buildozer/android/platform/android-sdk --ndk_dir=/home/hazhir/.buildozer/android/platform/android-ndk-r19c --bootstrap=sdl2 --dist_name=geniustmusicplayer --android_api=29 --name="GeniusT Music Player" --version=0.23 --package=org.allerter.geniustmusicplayer --requirements=python3,kivy==2.0.0,https://github.com/kivymd/KivyMD/archive/master.zip,pillow,android,sdl2_ttf==2.0.15,requests,urllib3,idna,chardet,oscpy,mutagen --orientation=portrait --window --private=/home/hazhir/Desktop/python/geniustmusicplayer/geniustmusicplayer --permission=INTERNET --permission=ACCESS_NETWORK_STATE --permission=READ_EXTERNAL_STORAGE --permission=WRITE_EXTERNAL_STORAGE --permission=FOREGROUND_SERVICE --service=gtplayer:./service.py --depend="com.android.support:support-compat:28.0.0" --depend="androidx.legacy:legacy-support-v4:1.0.0" --presplash-lottie /home/hazhir/Desktop/python/geniustmusicplayer/geniustmusicplayer/images/presplash.json --presplash-color white --icon="/home/hazhir/Desktop/python/geniustmusicplayer/geniustmusicplayer/images/icon.png"
`