#!/usr/bin/env bash

function run_cmd() {
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null deploy@$SERVER_IP "$*"
}

eval $(ssh-agent)
ssh-add - <<< $SSH_KEY
run_cmd "git -C Hermes fetch origin master"
run_cmd "git -C Hermes reset --hard origin/master"
run_cmd "/home/deploy/Hermes/venv/bin/pip install -U -r /home/deploy/Hermes/requirements.txt"
run_cmd "sudo systemctl restart hermes"
eval $(ssh-agent -k)
