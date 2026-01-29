import os
from huggingface_hub import snapshot_download
from tools.logger import log

def download():
    # 获取 main.py 同级目录的 models 路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, "models", "text2vec-base-chinese")
    
    log(f"开始下载模型到本地目录: {target_dir}")
    
    try:
        # 执行下载
        snapshot_download(
            repo_id="shibing624/text2vec-base-chinese",
            local_dir=target_dir,
            local_dir_use_symlinks=False  # 确保下载的是实体文件而非软链接
        )
        log("模型下载成功✓")
        log(f"请将 {target_dir} 文件夹上传到服务器对应位置。")
    except Exception as e:
        log(f"下载失败: {e}", level="ERROR")

if __name__ == "__main__":
    download()
