# 贡献指南

感谢你对 ChromaBead 的关注！我们欢迎任何形式的贡献，包括但不限于报告 Bug、提出新功能、改进文档或提交代码。请遵循以下指南，让协作更顺畅。

## 如何报告 Bug

如果你在使用过程中遇到了问题，请先检查 [已有 Issue](https://github.com/zhoufei0826/ChromaBead/issues) 是否已经涵盖了相同情况。如果没有，请创建一个新的 Issue，并尽可能提供以下信息：

- **操作系统**（如 Windows 11 / macOS 14 / Ubuntu 22.04）
- **Python 版本**（在终端运行 `python --version`）
- **ChromaBead 版本**（如 v1.0.0 或 commit hash）
- **复现步骤**：详细描述你的操作流程，最好附上截图或录屏。
- **预期行为 vs 实际行为**：你希望发生什么，实际发生了什么。

## 如何提交功能请求

如果你有新的功能想法或改进建议，也请先搜索已有 Issue，避免重复。提交时请说明：

- **功能描述**：这个功能是做什么的？
- **使用场景**：在什么情况下会用到这个功能？
- **替代方案**（可选）：有没有当前的变通方法？

## 本地开发环境搭建

如果你想对代码进行修改或调试，请按以下步骤搭建本地开发环境：

1. **克隆仓库**
   ```bash
   git clone https://github.com/zhoufei0826/ChromaBead.git
   cd ChromaBead
   ```
2. **创建虚拟环境**
    ```bash
    conda activate ChromaBead
    python main_gui.py
    ```
3. **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
3. **运行程序**
    ```bash
    python main_gui.py
    ```

## 代码风格要求
- 使用有意义的变量名和函数名，保持注释清晰（尤其是对算法部分的说明）。
- 提交前请检查是否有遗漏的 import 或未使用的变量。
- 对于 UI 相关改动，请确保在不同分辨率下界面布局基本正常。

## pull request
1. Fork 仓库 并切换到 dev 分支（如果有）或 main 分支。

2. 创建功能分支：git checkout -b feature/your-feature-name。

3. 进行修改，并确保代码能够正常运行。

4. 提交前自测：至少测试一次基本的“加载图片 → 生成图纸 → 保存”流程。

5. 提交代码：

    - 提交信息应清晰描述改动内容，例如 Fix: 修复加载大图时的内存溢出问题。

    - 如果有关联的 Issue，请在提交信息中引用（如 Closes #123）。

6. 推送到你的远程仓库：git push origin feature/your-feature-name。

7. 在 GitHub 上创建 Pull Request，选择 main 作为目标分支，并描述你的改动内容。

8. 等待代码审查，如有反馈请及时调整。

-----
感谢你的贡献！🎉
-------