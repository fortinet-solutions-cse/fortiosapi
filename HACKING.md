# Push to pypi
rm -rf dist/ <br>
python setup.py sdist bdist_wheel --universal <br>
twine upload dist/* <br>

# git tags
git tag -a v0.6.1 -m "Major release autotest and py3" <br>
git push origin --tags <br>

# unit test run
cd .tox/py27 <br>
. bin/activate  <br>
python -m unittest test_fortiosapi_virsh.TestFortinetRestAPI.test_00login test_fortiosapi_virsh.TestFortinetRestAPI.test_central_management
