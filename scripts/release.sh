# tag, commit, push, publish

# git commit and tag
git commit -a -m $1
git tag -a $1 -m $1
git push
git push --tags

python setup.py sdist bdist_wheel
scp dist/futurefire-$1.dev0.tar.gz snorris@hillcrestgeo.ca:/var/www/hillcrestgeo.ca/html/pypi/futurefire

echo 'Latest uploaded. Now go bump version and commit'