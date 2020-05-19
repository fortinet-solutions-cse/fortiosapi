### Explanation about certificates to test validity with the api and auth with cert

From: https://cookbook.fortinet.com/preventing-certificate-warnings-self-signed-60/
```bash
openssl genrsa -aes256 -out fgcaprivkey.pem 2048 -config openssl cnf

```
Enter a passphrase.


Interactive creation of the x509
```bash
openssl req -new -x509 -days 3650 -extensions v3_ca -key fgcaprivkey.pem -out fgcacert.pem -config openssl.cnf

```

With a predefined .cnf
```bash
openssl req -new -x509 -days 3650 -extensions v3_ca -key fgcaprivkey.pem -out fgcacert.pem

```

Excellent gist on creating cert : https://gist.github.com/fntlnz/cf14feb5a46b2eda428e000157447309
And Makefile: https://diagrams.mingrammer.com/docs/getting-started/examples
```bash
openssl req -in 40domain.com.csr -noout -text
openssl x509 -req -in 40domain.com.csr -CA fgcacert.pem -CAkey fgcaprivkey.pem -CAcreateserial -out 40domain.com.crt -days 500 -sha256
```

Then can upload to the Fortigate as a certificate.
You need to resolve 40domain to make it work, can use IP instead of 40domain