# gric

Gitlab registry image cleaner

Recursive remove images by tag

without wait 200ok please (some images very big, and response is very long)

```bash
docker run -it \
--name gitlab_cleaner \
--restart=always \
-d -p 8888:8888 \
-e CLEAN_TOKEN='mysecret key' \
-v /var/opt/gitlab/gitlab-rails/shared/registry/docker/registry/v2:/var/opt/gitlab/gitlab-rails/shared/registry/docker/registry/v2 \
negash/gric python3 \
-m japronto clean_gitlab_registry.app \
--worker-num 24 --port 8888
```