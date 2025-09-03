import os
import re
import csv
import pandas as pd



# df = pd.read_csv('./top-1m.csv',header=None)
# as_list = df.iloc[0:,1]

# as_list_top = list(as_list)[0:10000]
# print(len(as_list_top))



# print(as_list_top[0:10])

# exit()
# with open('./top10K.txt','w') as f:
#     for line in as_list_top:
#         f.write(line+'\n')

#     f.close()


df = pd.read_csv('./top-1m.csv', header=None)
as_list = df.iloc[:, 1].tolist()

batch_dict = {}
batch_size = 100000

for i in range(0, 1000000, batch_size):
    batch_key = f"batch_{i}_{i + batch_size - 1}.txt"
    batch_dict[batch_key] = as_list[i:i + batch_size]

for key, batch in batch_dict.items():
    with open('./batches/'+key, 'w') as f:
        f.write('\n'.join(map(str, batch)))

print(batch_dict.keys())