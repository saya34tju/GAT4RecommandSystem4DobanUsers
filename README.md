# 基于注意力知识图谱的推荐任务



## 介绍

简单的引入物品侧属性信息，基于注意力知识图谱的推荐算法，通过三层图注意力网络的信息聚合后，该模型达到了更好的预测性能，并且通过约束后的注意力系数向用户提供了推荐原因

代码中做了大量注释，如果对本代码有疑问，请联系我：
@author: Zhongming (zhongming@tju.edu.cn)

尝试了CKE，ECFKG，BPRFM等多个模型，但是目前训练时收敛不了，不知道什么原因，后期继续把这部分代码进行完善。
## 运行


* FM
```
python main_nfm.py --model_type fm --data_name amazon-book
```
* NFM
```
python main_nfm.py --model_type nfm --data_name amazon-book
```
* KGAT
```
python main_kgat.py --data_name amazon-book
```
## 数据集

爬取豆瓣电影Top250的用户观影评价信息，此外为了验证大规模数据集的效果，同时收集了amazon-book, last-fm, yelp数据库等，对比算法我们采用了FM, NFM等
