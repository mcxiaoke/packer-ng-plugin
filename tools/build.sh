# @Author: mcxiaoke
# @Date:   2017-06-16 17:07:06
# @Last Modified by:   mcxiaoke
# @Last Modified time: 2017-06-16 17:11:47
#!/usr/bin/env bash
cd src
make && make install && make clean
cd ..
packer
exit
