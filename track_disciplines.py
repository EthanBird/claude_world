import os
import json
from pathlib import Path
import shutil
import sys

# 基础目录
BASE_DIR = 'expanded/academia'

def find_json_files(directory):
    """递归查找所有JSON文件"""
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def build_discipline_tree():
    """构建学科层次结构树"""
    discipline_tree = {}
    
    # 获取所有目录
    for root, dirs, files in os.walk(BASE_DIR):
        if root == BASE_DIR:
            continue
        
        relative_path = os.path.relpath(root, BASE_DIR)
        path_parts = relative_path.split(os.sep)
        
        # 构建嵌套字典
        current = discipline_tree
        for part in path_parts:
            # 检查目录名是否带有"(未完成)"标记
            is_incomplete = "(未完成)" in part
            clean_part = part.replace("(未完成)", "").strip()
            
            if clean_part not in current:
                current[clean_part] = {
                    "_is_completed": not is_incomplete,
                    "_original_name": part,
                    "_path": os.path.join(BASE_DIR, os.path.join(*path_parts[:path_parts.index(part)+1])),
                    "_files": []
                }
            current = current[clean_part]
        
        # 添加JSON文件
        for file in files:
            if file.endswith('.json'):
                current["_files"].append(file)
    
    # 标记末端学科
    mark_leaf_disciplines(discipline_tree)
    
    return discipline_tree

def mark_leaf_disciplines(tree):
    """标记末端学科节点"""
    is_leaf = True
    
    for key, value in tree.items():
        if key.startswith('_'):
            continue
        
        is_leaf = False
        mark_leaf_disciplines(value)
    
    tree["_is_leaf"] = is_leaf

def get_incomplete_disciplines(tree, current_path=None):
    """获取所有未完成的末端学科"""
    if current_path is None:
        current_path = []
    
    result = []
    
    for key, value in tree.items():
        if key.startswith('_'):
            continue
        
        new_path = current_path + [key]
        
        # 如果是末端学科且未完成，添加到结果中
        if value.get("_is_leaf", False) and not value.get("_is_completed", False):
            result.append(new_path)
        else:
            # 递归检查子学科
            result.extend(get_incomplete_disciplines(value, new_path))
    
    return result

def get_all_leaf_disciplines(tree, current_path=None):
    """获取所有末端学科，无论完成状态"""
    if current_path is None:
        current_path = []
    
    result = []
    
    for key, value in tree.items():
        if key.startswith('_'):
            continue
        
        new_path = current_path + [key]
        
        # 如果是末端学科，添加到结果中
        if value.get("_is_leaf", False):
            result.append((new_path, value.get("_is_completed", False)))
        else:
            # 递归检查子学科
            result.extend(get_all_leaf_disciplines(value, new_path))
    
    return result

def mark_discipline_completed(tree, path):
    """将指定路径的学科标记为已完成，并重命名目录"""
    current = tree
    for i, part in enumerate(path):
        if part in current:
            if i == len(path) - 1:  # 最后一个部分
                current[part]["_is_completed"] = True
                
                # 重命名目录
                old_path = current[part].get("_path")
                if old_path and "(未完成)" in os.path.basename(old_path):
                    new_name = os.path.basename(old_path).replace("(未完成)", "").strip()
                    new_path = os.path.join(os.path.dirname(old_path), new_name)
                    
                    try:
                        # 重命名目录
                        shutil.move(old_path, new_path)
                        current[part]["_path"] = new_path
                        current[part]["_original_name"] = new_name
                        print(f"目录已重命名: {old_path} -> {new_path}")
                    except Exception as e:
                        print(f"重命名目录时出错: {e}")
            
            current = current[part]
        else:
            return False
    
    return True

def mark_discipline_incomplete(tree, path):
    """将指定路径的学科标记为未完成，并重命名目录"""
    current = tree
    for i, part in enumerate(path):
        if part in current:
            if i == len(path) - 1:  # 最后一个部分
                current[part]["_is_completed"] = False
                
                # 重命名目录
                old_path = current[part].get("_path")
                if old_path and "(未完成)" not in os.path.basename(old_path):
                    new_name = f"{os.path.basename(old_path)} (未完成)"
                    new_path = os.path.join(os.path.dirname(old_path), new_name)
                    
                    try:
                        # 重命名目录
                        shutil.move(old_path, new_path)
                        current[part]["_path"] = new_path
                        current[part]["_original_name"] = new_name
                        print(f"目录已重命名: {old_path} -> {new_path}")
                    except Exception as e:
                        print(f"重命名目录时出错: {e}")
            
            current = current[part]
        else:
            return False
    
    return True

def print_discipline_tree(tree, indent=0, path=None):
    """打印学科层次结构"""
    if path is None:
        path = []
    
    for key, value in sorted(tree.items()):
        if not key.startswith('_'):
            status = " (已完成)" if value.get("_is_completed", False) else " (未完成)"
            leaf_mark = " [末端]" if value.get("_is_leaf", False) else ""
            print("  " * indent + f"- {key}{status}{leaf_mark}")
            print_discipline_tree(value, indent + 1, path + [key])

def save_state(tree, filename="discipline_state.json"):
    """保存当前状态到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

def load_state(filename="discipline_state.json"):
    """从文件加载状态，如果文件不存在则重新构建"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return build_discipline_tree()

def modify_directory_names(tree, base_path=BASE_DIR):
    """初始化目录名称，为未完成的末端学科添加标记"""
    for key, value in tree.items():
        if key.startswith('_'):
            continue
        
        current_path = os.path.join(base_path, key)
        
        # 如果是末端学科且未完成，添加标记
        if value.get("_is_leaf", False) and not value.get("_is_completed", False):
            if os.path.exists(current_path) and "(未完成)" not in key:
                new_path = os.path.join(base_path, f"{key} (未完成)")
                try:
                    shutil.move(current_path, new_path)
                    print(f"标记未完成: {current_path} -> {new_path}")
                    value["_path"] = new_path
                    value["_original_name"] = f"{key} (未完成)"
                except Exception as e:
                    print(f"重命名目录时出错: {e}")
        
        # 递归处理子目录
        modify_directory_names(value, current_path)

def list_directories():
    """列出所有目录"""
    result = []
    for root, dirs, files in os.walk(BASE_DIR):
        for dir_name in dirs:
            full_path = os.path.join(root, dir_name)
            result.append(full_path)
    return result

def reset_specific_disciplines(tree, disciplines_to_reset):
    """重置特定学科的状态为未完成"""
    for discipline_path in disciplines_to_reset:
        path_parts = discipline_path.split("/")
        mark_discipline_incomplete(tree, path_parts)
    
    # 保存状态
    save_state(tree)
    
    print("\n已将以下学科标记为未完成:")
    for discipline in disciplines_to_reset:
        print(f"- {discipline}")

def main():
    # 检查是否有命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        # 重置特定学科
        disciplines_to_reset = [
            # 在此列出要重置的学科路径，例如:
            "人文学科/哲学/道家哲学",
            "人文学科/哲学/法家哲学",
            "人文学科/哲学/墨家哲学",
            "人文学科/哲学/名家",
            "人文学科/哲学/农家",
            "人文学科/哲学/阴阳家",
            "人文学科/哲学/兵家",
            "人文学科/哲学/纵横家",
            "人文学科/哲学/小说家",
            "人文学科/哲学/杂家"
        ]
        tree = load_state()
        reset_specific_disciplines(tree, disciplines_to_reset)
        return

    # 加载或创建学科状态
    print("正在构建学科层次结构...")
    discipline_tree = build_discipline_tree()
    
    # 打印当前学科结构
    print("\n当前学科层次结构:")
    print_discipline_tree(discipline_tree)
    
    # 保存状态
    save_state(discipline_tree)
    
    # 获取未完成的末端学科
    incomplete = get_incomplete_disciplines(discipline_tree)
    print(f"\n共有 {len(incomplete)} 个未完成的末端学科")
    
    if incomplete:
        next_discipline = incomplete[0]
        print(f"\n下一个要处理的学科: {' / '.join(next_discipline)}")
        
        # 获取该学科的完整路径
        discipline_path = BASE_DIR
        current = discipline_tree
        for part in next_discipline:
            discipline_path = os.path.join(discipline_path, current[part].get("_original_name", part))
            current = current[part]
        
        print(f"完整路径: {discipline_path}")
        
        # 要遵循的处理格式
        print("\n按照以下格式处理此学科:")
        print("1、修改完成的末端学科状态（修改文件夹名字[删除未完成]），获取当前任务的目录")
        print("2、判定当前目录是否全部完成")
        print("3、选择下一个未完成的末端学科目录，并记录完整文件目录")
        print("4、重复输出这四个要点，以防遗忘")
        
        # 这里可以添加交互式处理逻辑
        choice = input("\n是否标记此学科为已完成？(y/n): ").strip().lower()
        if choice == 'y':
            mark_discipline_completed(discipline_tree, next_discipline)
            save_state(discipline_tree)
            
            print("\n1、已修改完成的末端学科状态（已删除'未完成'标记）")
            
            # 检查是否所有学科都已完成
            incomplete = get_incomplete_disciplines(discipline_tree)
            if len(incomplete) == 0:
                print("2、当前目录所有学科已全部完成")
                print("3、没有未完成的末端学科目录")
            else:
                print(f"2、当前目录仍有 {len(incomplete)} 个未完成的学科")
                next_discipline = incomplete[0]
                print(f"3、下一个未完成的末端学科目录: {' / '.join(next_discipline)}")
                
                # 获取该学科的完整路径
                discipline_path = BASE_DIR
                current = discipline_tree
                for part in next_discipline:
                    discipline_path = os.path.join(discipline_path, current[part].get("_original_name", part))
                    current = current[part]
                
                print(f"   完整文件路径: {discipline_path}")
            
            print("4、请记住处理格式：1.修改状态 2.判断完成情况 3.选择下一个 4.重复这四点")
    else:
        print("所有学科均已完成! 如需重置某些学科状态，请使用 'python track_disciplines.py reset' 命令。")

def list_all_disciplines():
    """列出所有末端学科及其完成状态"""
    tree = build_discipline_tree()
    all_disciplines = get_all_leaf_disciplines(tree)
    
    print("所有末端学科及其状态:")
    for path, is_completed in all_disciplines:
        status = "已完成" if is_completed else "未完成"
        print(f"- {' / '.join(path)} ({status})")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_all_disciplines()
    else:
        main() 