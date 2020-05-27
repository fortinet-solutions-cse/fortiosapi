
## Hacking development tips

### Push to pypi

Follow: https://packaging.python.org/tutorials/packaging-projects/#description 

Quick:
```bash
 rm -rf dist/
 python3 setup.py sdist bdist_wheel --universal 
 python3 -m twine upload dist/* --verbose --cert /etc/ssl/certs/
```

### git tags

```bash
git tag -a v1.0.1 -m "GA release with Verify of SSL on by default"
git push origin --tags 
```


### Run only 1 unit test


```bash
cd .tox/py27 
. bin/activate  
python -m unittest test_fortiosapi_virsh.TestFortinetRestAPI.test_00login test_fortiosapi_virsh.TestFortinetRestAPI.test_central_management

```
