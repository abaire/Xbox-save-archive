#!/usr/bin/env python3
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    token = os.environ.get("GH_TOKEN")
    upload_url_base = os.environ.get("UPLOAD_URL")
    artifacts_dir = sys.argv[1] if len(sys.argv) > 1 else "artifacts"

    if not token or not upload_url_base:
        sys.exit("Error: GH_TOKEN and UPLOAD_URL environment variables are required.")

    if not os.path.isdir(artifacts_dir):
        sys.exit(f"Error: Directory '{artifacts_dir}' does not exist.")

    files = [f for f in os.listdir(artifacts_dir) if f.endswith(".zip")]
    files.sort()
    total = len(files)
    print(f"Total files to upload: {total}")

    for i, filename in enumerate(files, 1):
        filepath = os.path.join(artifacts_dir, filename)
        encoded_name = urllib.parse.quote(filename)
        url = f"{upload_url_base}?name={encoded_name}"
        file_size = os.path.getsize(filepath)

        max_retries = 5
        delay = 3

        for attempt in range(max_retries):
            try:
                with open(filepath, "rb") as f:
                    data = f.read()

                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/zip",
                        "Content-Length": str(file_size),
                        "User-Agent": "actions-release-script",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req) as resp:
                    if resp.status in (200, 201):
                        print(f"[{i}/{total}] Uploaded: {filename}")
                        break

            except urllib.error.HTTPError as e:
                # Handle secondary rate limits (403), rate limits (429), or transient gateway drops
                if e.code in (403, 429, 500, 502, 503):
                    print(
                        f"[{i}/{total}] HTTP {e.code} on {filename}. Backing off {delay}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    body = e.read().decode("utf-8", errors="ignore")
                    sys.exit(
                        f"[{i}/{total}] Failed permanently: {filename} -> HTTP {e.code}: {body}"
                    )
            except Exception as e:
                print(
                    f"[{i}/{total}] Network error on {filename}: {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay *= 2
        else:
            sys.exit(f"[{i}/{total}] Exceeded max retries for {filename}")

        # Pacing delay to avoid triggering GitHub abuse heuristics
        time.sleep(0.3)


if __name__ == "__main__":
    main()
