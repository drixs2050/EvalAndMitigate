#!/usr/bin/env bash

# Check if d4j_home is provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <d4j_home>"
    exit 1
fi

# Assign the first argument to d4j_home
d4j_home=$1

# Directory where JARs will be placed
LIB_DIR="$d4j_home/framework/projects/lib"
mkdir -p "$LIB_DIR"

# Array of dependencies to download: (URL FILENAME)
# Feel free to adjust versions if needed.
deps=(
    "https://repo1.maven.org/maven2/org/mockito/mockito-core/3.12.4/mockito-core-3.12.4.jar mockito-core-3.12.4.jar"
    "https://repo1.maven.org/maven2/org/mockito/mockito-junit-jupiter/3.12.4/mockito-junit-jupiter-3.12.4.jar mockito-junit-jupiter-3.12.4.jar"
    "https://repo1.maven.org/maven2/org/junit/jupiter/junit-jupiter-params/5.0.0/junit-jupiter-params-5.0.0.jar junit-jupiter-params-5.0.0.jar"
    "https://repo1.maven.org/maven2/org/junit/jupiter/junit-jupiter-api/5.7.2/junit-jupiter-api-5.7.2.jar junit-jupiter-api-5.7.2.jar"
    "https://repo1.maven.org/maven2/org/apiguardian/apiguardian-api/1.1.0/apiguardian-api-1.1.0.jar apiguardian-api-1.1.0.jar"
    "https://repo1.maven.org/maven2/net/bytebuddy/byte-buddy/1.14.11/byte-buddy-1.14.11.jar byte-buddy-1.14.11.jar"
    "https://repo1.maven.org/maven2/net/bytebuddy/byte-buddy-agent/1.14.11/byte-buddy-agent-1.14.11.jar byte-buddy-agent-1.14.11.jar"
    "https://repo1.maven.org/maven2/org/objenesis/objenesis/3.3/objenesis-3.3.jar objenesis-3.3.jar"
    "https://repo1.maven.org/maven2/org/hamcrest/hamcrest/2.1/hamcrest-2.1.jar hamcrest-2.1.jar"
    "https://repo1.maven.org/maven2/org/powermock/powermock-api-mockito2/1.7.4/powermock-api-mockito2-1.7.4.jar powermock-api-mockito2-1.7.4.jar"
    "https://repo1.maven.org/maven2/org/powermock/powermock-core/1.7.4/powermock-core-1.7.4.jar powermock-core-1.7.4.jar"
    "https://repo1.maven.org/maven2/org/powermock/powermock-module-junit4/1.7.4/powermock-module-junit4-1.7.4.jar powermock-module-junit4-1.7.4.jar"
)

echo "Downloading dependencies to $LIB_DIR ..."

for dep in "${deps[@]}"; do
    url=$(echo "$dep" | awk '{print $1}')
    filename=$(echo "$dep" | awk '{print $2}')

    echo "Downloading $filename from $url ..."
    curl -fLo "$LIB_DIR/$filename" "$url"
    if [ $? -ne 0 ]; then
        echo "Failed to download $filename from $url"
        exit 1
    fi
done

echo "All dependencies downloaded successfully to $LIB_DIR."
