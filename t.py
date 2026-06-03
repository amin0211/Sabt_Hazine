cd ~/Projects/SabtHazineha

deactivate 2>/dev/null || true

# ===============================
# 1) Android venv outside project
# ===============================

if [ ! -d ~/Projects/SabtHazineha_venv_android ]; then
  python3.13 -m venv ~/Projects/SabtHazineha_venv_android
fi

source ~/Projects/SabtHazineha_venv_android/bin/activate

which python
python -m pip install --upgrade pip

# ===============================
# 2) Use Android config
# ===============================

cp pyproject_android.toml pyproject.toml
cp requirements_android.txt requirements.txt

python -m pip install -r requirements.txt

# ===============================
# 3) Compile check
# ===============================

python -m py_compile main.py
python -m py_compile services/voice_service_router.py
python -m py_compile services/voice_service_android.py

# ===============================
# 4) Clean old build and macOS junk
# ===============================

rm -rf build

export COPYFILE_DISABLE=1
find ~/Projects/SabtHazineha -name "._*" -delete
find ~/Projects/SabtHazineha -name ".DS_Store" -delete
xattr -cr ~/Projects/SabtHazineha

# ===============================
# 5) Java / Android setup
# ===============================

export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

java -version

# ===============================
# 6) Android signing
# مسیر keystore و پسوردها را درست کن
# ===============================

export FLET_ANDROID_SIGNING_KEY_STORE="$HOME/upload-keystore.jks"
export FLET_ANDROID_SIGNING_KEY_ALIAS="upload"
export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="YOUR_KEYSTORE_PASSWORD"
export FLET_ANDROID_SIGNING_KEY_PASSWORD="YOUR_KEY_PASSWORD"

# ===============================
# 7) First Flet build to generate Android wrapper
# ===============================

flet build aab . -v \
  --project costio \
  --product Costio \
  --org com.pps \
  --bundle-id com.pps.costio \
  --build-number 18 \
  --build-version 1.0.18 \
  --skip-flutter-doctor

# ===============================
# 8) Copy custom Android files
# ===============================

PROJECT_DIR="$HOME/Projects/SabtHazineha"

if [ -f "$PROJECT_DIR/flutter_android/AndroidManifest.xml" ]; then
  cp "$PROJECT_DIR/flutter_android/AndroidManifest.xml" \
     "$PROJECT_DIR/build/flutter/android/app/src/main/AndroidManifest.xml"
  echo "Copied AndroidManifest.xml"
else
  echo "SKIP: flutter_android/AndroidManifest.xml not found"
fi

if [ -f "$PROJECT_DIR/flutter_android/build.gradle.kts" ]; then
  cp "$PROJECT_DIR/flutter_android/build.gradle.kts" \
     "$PROJECT_DIR/build/flutter/android/app/build.gradle.kts"
  echo "Copied build.gradle.kts"
else
  echo "SKIP: flutter_android/build.gradle.kts not found"
fi

MAIN_ACTIVITY_TARGET="$PROJECT_DIR/build/flutter/android/app/src/main/kotlin/com/pps/costio/MainActivity.kt"
mkdir -p "$(dirname "$MAIN_ACTIVITY_TARGET")"

if [ -f "$PROJECT_DIR/flutter_android/MainActivity.kt" ]; then
  cp "$PROJECT_DIR/flutter_android/MainActivity.kt" "$MAIN_ACTIVITY_TARGET"
  echo "Copied MainActivity.kt"
else
  echo "SKIP: flutter_android/MainActivity.kt not found"
fi

if [ -f "$PROJECT_DIR/flutter_android/local.properties" ]; then
  cp "$PROJECT_DIR/flutter_android/local.properties" \
     "$PROJECT_DIR/build/flutter/android/local.properties"
  echo "Copied local.properties"
else
  echo "SKIP: flutter_android/local.properties not found"
fi

# ===============================
# 9) Rebuild AAB after custom Android patches
# ===============================

cd "$PROJECT_DIR/build/flutter/android"

export SERIOUS_PYTHON_SITE_PACKAGES="$PROJECT_DIR/build/site-packages"

./gradlew clean
./gradlew bundleRelease

# ===============================
# 10) Copy final AAB outside project
# ===============================

mkdir -p ~/Projects/SabtHazineha_android_outputs

AAB_PATH=$(find "$PROJECT_DIR/build/flutter" -name "*.aab" -print | head -1)

echo "AAB_PATH=$AAB_PATH"

if [ -n "$AAB_PATH" ]; then
  cp "$AAB_PATH" ~/Projects/SabtHazineha_android_outputs/costio-1.0.18-18.aab
  echo "Copied final AAB:"
  ls -lh ~/Projects/SabtHazineha_android_outputs/costio-1.0.18-18.aab
else
  echo "ERROR: No .aab file found."
fi

# ===============================
# 11) Size check
# ===============================

du -sh "$PROJECT_DIR/build" 2>/dev/null || true
du -sh ~/Projects/SabtHazineha_android_outputs/costio-1.0.18-18.aab 2>/dev/null || true