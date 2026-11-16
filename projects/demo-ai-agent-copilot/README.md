# Devpost Global AI Agent Hackathon: Pitch & Architecture Copilot

> 自动由 **CloudAgentCluster** 基于中转网站 Spec/Plan 构建的全栈 Hackathon 参赛项目。

- **Slug**: `demo-ai-agent-copilot`
- **参赛平台**: `devpost`
- **原始比赛链接**: https://devpost.com/hackathons
- **简介**: 面向极客马拉松选手的实时项目架构评估与路演提纲生成全栈应用。

## 快速启动

```bash
python backend/server.py
```

启动后在浏览器访问 `http://127.0.0.1:8000` 即可体验完整前端与后端 API。

## 运行自动化测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 设计文档
- [SPEC.md](SPEC.md)
- [PLAN.md](PLAN.md)
