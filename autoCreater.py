import os

# 確保目錄存在
os.makedirs("./levels/example", exist_ok=True)

# 從 3 到 20
for i in range(21, 31):
    filename = f"./levels/examples/custom_level_{i}.py"
    
    # 每個關卡的基本模板
    content = f'''# 自動生成關卡 {i}
level_data = {{
    "name": "自動關卡 {i}",
    "blocks": [
        {{"pos": [0, 0, 0], "color": 1}},
        {{"pos": [0, 1, 0], "color": 2}},
        {{"pos": [1, 0, 0], "color": 3}}
    ]
}}

# 你可以在這裡修改 blocks 或用數學公式自動生成
'''

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

print("關卡文件已生成完成！")
