# Push to pypi

```bash
rm -rf dist/
python setup.py sdist bdist_wheel --universal
twine upload dist/*
```

# git tags

```bash
git tag -a v0.6.1 -m "Major release autotest and py3" <br>
git push origin --tags <br>
```

# unit test run

```
cd .tox/py27
. bin/activate
python -m unittest test_fortiosapi_virsh.TestFortinetRestAPI.test_00login test_fortiosapi_virsh.TestFortinetRestAPI.test_central_management
```
