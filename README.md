# ko-mei project は以下2つのDocker 環境で稼働する
## ✔ Container ollama
## ✔ Container ko-mei

# <作業用ディレクトリへ移動>
cd ko-mei-project/

# <起動>
docker compose up -d

# <停止>
docker compose down

# <Dockerに入る>
## localLLM モデルは "ollama"のDocker 環境に格納されているので、操作する場合は Docker 内で作業する。
docker exec -it ollama bash

## FEの作問作業は "ko-mei" の Docker 環境で作業する必要がある。
docker exec -it ko-mei bash

# <個別のサーバー停止/再起動>
# 停止
docker stop ko-mei

# 起動
docker start ko-mei

# 再起動
docker restart ko-mei

#<モデル確認>
ollama list