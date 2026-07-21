import glob
import json
import os
import subprocess
import threading
import uuid

from flask import Flask, jsonify, request, send_file


app = Flask(__name__)
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.join(os.getcwd(), "downloads"))
YTDLP_COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", "")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs: dict[str, dict] = {}


def build_ytdlp_cmd(base_cmd: list[str]) -> list[str]:
    if YTDLP_COOKIES_FILE and os.path.isfile(YTDLP_COOKIES_FILE):
        return [*base_cmd, "--cookies", YTDLP_COOKIES_FILE]
    return base_cmd


def run_download(job_id: str, url: str, format_choice: str, format_id: str | None) -> None:
    job = jobs[job_id]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    cmd = build_ytdlp_cmd(["yt-dlp", "--no-playlist", "-o", out_template])

    if format_choice == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    elif format_id:
        cmd += ["-f", f"{format_id}+bestaudio/best", "--merge-output-format", "mp4"]
    else:
        cmd += ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            job["status"] = "error"
            job["error"] = result.stderr.strip().split("\n")[-1]
            return

        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{job_id}.*"))
        if not files:
            job["status"] = "error"
            job["error"] = "Download completed but no file was found"
            return

        if format_choice == "audio":
            target = [file_name for file_name in files if file_name.endswith(".mp3")]
        else:
            target = [file_name for file_name in files if file_name.endswith(".mp4")]
        chosen = target[0] if target else files[0]

        for file_name in files:
            if file_name != chosen:
                try:
                    os.remove(file_name)
                except OSError:
                    pass

        job["status"] = "done"
        job["file"] = chosen
        ext = os.path.splitext(chosen)[1]
        title = job.get("title", "").strip()
        if title:
            safe_title = "".join(char for char in title if char not in r'\/:*?"<>|').strip()[:80].strip()
            job["filename"] = f"{safe_title}{ext}" if safe_title else os.path.basename(chosen)
        else:
            job["filename"] = os.path.basename(chosen)
    except subprocess.TimeoutExpired:
        job["status"] = "error"
        job["error"] = "Download timed out (5 min limit)"
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)


@app.route("/")
def index():
    return "downloader ok", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.json or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    cmd = build_ytdlp_cmd(["yt-dlp", "--no-playlist", "-j", url])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return jsonify({"error": result.stderr.strip().split("\n")[-1]}), 400

        info = json.loads(result.stdout)
        best_by_height: dict[int, dict] = {}
        for fmt in info.get("formats", []):
            height = fmt.get("height")
            if height and fmt.get("vcodec", "none") != "none":
                tbr = fmt.get("tbr") or 0
                if height not in best_by_height or tbr > (best_by_height[height].get("tbr") or 0):
                    best_by_height[height] = fmt

        formats = []
        direct_url = info.get("url")
        for height, fmt in best_by_height.items():
            if not direct_url and fmt.get("url") and fmt.get("acodec", "none") != "none":
                direct_url = fmt.get("url")
            formats.append(
                {
                    "id": str(fmt["format_id"]),
                    "label": f"{height}p",
                    "height": height,
                }
            )
        formats.sort(key=lambda item: item["height"], reverse=True)

        return jsonify(
            {
                "title": info.get("title", ""),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", ""),
                "formats": formats,
                "direct_url": direct_url,
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timed out fetching video info"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json or {}
    url = (data.get("url") or "").strip()
    format_choice = data.get("format", "video")
    format_id = data.get("format_id")
    title = data.get("title", "")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = uuid.uuid4().hex[:10]
    jobs[job_id] = {"status": "downloading", "url": url, "title": title}
    thread = threading.Thread(
        target=run_download,
        args=(job_id, url, format_choice, format_id),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def check_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(
        {
            "status": job["status"],
            "error": job.get("error"),
            "filename": job.get("filename"),
        }
    )


@app.route("/api/file/<job_id>")
def download_file(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "File not ready"}), 404
    return send_file(job["file"], as_attachment=True, download_name=job["filename"])


def main() -> None:
    import logging

    logging.basicConfig(level=logging.INFO)
    if YTDLP_COOKIES_FILE and os.path.isfile(YTDLP_COOKIES_FILE):
        logging.info("yt-dlp cookies enabled: %s", YTDLP_COOKIES_FILE)
    else:
        logging.warning(
            "yt-dlp cookies file not found at %s — YouTube fallback may fail on datacenter IPs",
            YTDLP_COOKIES_FILE or "(not configured)",
        )

    port = int(os.environ.get("PORT", "8899"))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
