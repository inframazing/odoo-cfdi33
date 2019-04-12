FROM registry.gitlab.com/desiteg/odoo-dg:latest
USER root

RUN apt-get install -y nano

RUN apt-get remove -y python-pip
RUN easy_install pip

# RUN pip install googlemaps
# RUN pip install OpenSSL
# RUN apt-get install -y libssl-dev

RUN pip install pyopenssl
RUN pip install pyqrcode
RUN pip install pypng
RUN pip install qrcode

COPY ./entrypoint.sh /entrypoint.sh
COPY ./config/odoo.conf /etc/odoo/odoo.conf
RUN chmod 777 /entrypoint.sh

RUN rm -dfr /mnt/desiteg/cfdi_invoice

COPY ./addons /mnt/cfdi

USER odoo