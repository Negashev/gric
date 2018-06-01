#!/usr/bin/python3

#
# Disclaimer: Dirty workaround, i'm not responsible for anything, although it works for us
#
# simple webhook script for https://gitlab.com/gitlab-org/gitlab-ce/issues/21608#note_22185264
# uses https://github.com/burnettk/delete-docker-registry-image
#
# listens on POST requests containing JSON data from Gitlab webhook (on merge)
# it uses bottlepy, so setup like:
#   pip install bottle
# you can run it like
#   nohup /opt/registry-cleanup/python/registry-cleaner.py >> /var/log/registry-cleanup.log 2>&1 &
# also you need to put delete-docker-registry-image into the same directory:
#   curl -O https://raw.githubusercontent.com/burnettk/delete-docker-registry-image/master/delete_docker_registry_image.py
#
# you should also run registry garbage collection, either afterwards (might break your productive env) or at night (cronjob, better)
# gitlab-ctl registry-garbage-collect

import asyncio
from japronto import Application
import delete_docker_registry_image
import logging
import os

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(u'%(levelname)-8s [%(asctime)s]  %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# basic sec urity, add this token to the project's webhook
# get one:
# < /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c"${1:-32}";echo;
token = os.getenv('CLEAN_TOKEN')

if 'DRY_RUN' in os.environ:
    dry_run = True
else:
    dry_run = False


async def validate(request):
    if 'clean-token' in request.query and request.query['clean-token'] == token:
        project_namespace = request.match_dict['project_namespace']
        project_name = request.match_dict['project_name']
        tag = request.match_dict['tag']
        logger.info(f"Valid request, processing {', '.join(request.match_dict.values())}")
        cleanup(project_namespace, project_name, tag)
        return request.Response(text='ok')

    return request.Response(text='request not valid')


def cleanup(project_namespace, project_name, tag):
    logger.info("Merge detected")
    registry_data_dir = os.getenv('REGISTRY_DATA_DIR',
                                  "/var/opt/gitlab/gitlab-rails/shared/registry/docker/registry/v2")
    this_repo_image = "%s/%s" % (project_namespace, project_name)

    untagged = False
    prune = True
    # find all images
    images = [this_repo_image]
    for i in os.listdir(f"{registry_data_dir}/repositories/{this_repo_image}"):
        if i not in ['_layers', '_manifests', '_uploads']:
            images.append(f"{this_repo_image}/{i}")
    # remove all images with this tag
    for image in images:
        logger.info("Trying to delete %s:%s" % (image, tag))
        try:
            cleaner = delete_docker_registry_image.RegistryCleaner(registry_data_dir, dry_run)
            if untagged:
                cleaner.delete_untagged(image)
            else:
                if tag:
                    cleaner.delete_repository_tag(image, tag)
                else:
                    cleaner.delete_entire_repository(image)

            if prune:
                cleaner.prune()
        except delete_docker_registry_image.RegistryCleanerError as error:
            logger.fatal(error)


app = Application()
router = app.router
router.add_route('/{project_namespace}/{project_name}/{tag}', validate)
app.run(host='0.0.0.0', port=80, debug=True)
