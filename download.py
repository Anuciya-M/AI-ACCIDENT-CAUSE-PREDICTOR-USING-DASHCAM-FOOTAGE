from huggingface_hub import snapshot_download

snapshot_download(repo_id="nexar-ai/nexar_collision_prediction", local_dir="nexar_dataset")
print("Download complete! Folder: nexar_dataset")