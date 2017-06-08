# Push to pypi
rm -rf dist/
python setup.py sdist bdist_wheel --universal
twine upload dist/*

# git tags
git tag -a v0.6-m "Major release autotest and py3"
git push origin --tags
