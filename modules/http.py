import logs as logging

import objectrest


def download_file(response: objectrest.Response, filename: str) -> bool:
    try:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
            f.close()
        return True
    except Exception as e:
        logging.error(f"Error downloading {filename}")
        return False
