#!/usr/bin/env bash

# shellcheck disable=SC2154

export DEBIAN_FRONTEND="noninteractive"
sudo apt update -y
sudo apt install python3 git nginx python3-certbot-nginx python3-pip firefox -y
cd /tmp || exit
wget -qO- https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz | sudo tar xvz -C /usr/local/bin/
sudo certbot --noninteractive --nginx --agree-tos --email akhilnarang@thescriptgroup.in --domain hermes.thescriptgroup.in
cat << EOF | sudo tee /etc/nginx/sites-available/hermes.thescriptgroup.in
server {
    listen 80;
    server_name hermes.thescriptgroup.in;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 301 https://hermes.thescriptgroup.in$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name hermes.thescriptgroup.in;
    ssl_certificate /etc/letsencrypt/live/hermes.thescriptgroup.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hermes.thescriptgroup.in/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location /static {
        root /home/hermes/Hermes/web_app;
        try_files \$uri \$uri/ =404;
    }

    location ^~ / {
        proxy_pass        http://127.0.0.1:8000;
        proxy_redirect    off;

        proxy_set_header   Host                 \$host;
        proxy_set_header   X-Real-IP            \$remote_addr;
        proxy_set_header   X-Forwarded-For      \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto    \$scheme;
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/hermes.thescriptgroup.in /etc/nginx/sites-enabled/hermes.thescriptgroup.in
sudo rm -fv /etc/nginx/sites-{available,enabled}/default
sudo nginx -s reload
echo '30 2 * * * /usr/bin/certbot renew --noninteractive --renew-hook "/usr/sbin/nginx -s reload" >> /var/log/le-renew.log' > /tmp/cron
sudo crontab /tmp/cron
rm -v /tmp/cron
cd - || exit
git clone https://github.com/The-SCRIPT-Group/Hermes.git
cd Hermes || exit
pip3 install -r requirements.txt
echo "Setup your configuration file and run the application! (make sure its running on port 8080, should be the default with waitress)"
