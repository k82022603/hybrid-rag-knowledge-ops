# hybrid-rag-knowledge-ops 프로젝트용 WSL2 설정
# Elasticsearch + AI Service(임베딩) + PostgreSQL + Docker Compose 기준
# 18개 컨테이너 전체 기동 시 ~11GB, 임베딩 파이프라인 추가 시 ~13GB
[wsl2]
memory=14GB
swap=4GB
processors=8

[experimental]
autoMemoryReclaim=dropcache
sparseVhd=true
