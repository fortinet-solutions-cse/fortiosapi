
https://open.riftio.com/documentation/riftware/4.3/a/install/install-riftware-prebuilt-container-docker.htm
docker pull riftio/launchpad:latest
docker run --privileged -d -p80:80 -p2024:2024 -p4567:4567 -p8000:8000 -p8008:8008 -p8443:8443 --name launchpad riftio/launchpad

usage https://open.riftio.com/documentation/riftware/4.3/a/onboarding-lcm/browse-to-riftware-ui.htm

8443 conflicts with LXD making it unpractical switching to lxd (might go with less broad ip redirect)
