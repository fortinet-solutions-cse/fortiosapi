# Push to pypi
Follow: https://packaging.python.org/tutorials/packaging-projects/#description 
Quick:
```bash
 rm -rf dist/
 python3 setup.py sdist bdist_wheel --universal 
 python3 -m twine upload dist/* --verbose
```
# git tags
git tag -a v0.10.7 -m "Add PR with better handled exceptions for login and License" 
git push origin --tags 

# unit test run
cd .tox/py27 
. bin/activate  
python -m unittest test_fortiosapi_virsh.TestFortinetRestAPI.test_00login test_fortiosapi_virsh.TestFortinetRestAPI.test_central_management
