# GitHub → Gitee 同步

- 源仓库：https://github.com/dushanaicode/dushan-ai-native
- 目标仓库：https://gitee.com/dushan-ai/dushan-ai-native
- 工作流：`Sync to Gitee`，GitHub 分支或标签推送后自动运行，也可以在 Actions 页面手动运行。
- 同步分支与标签；不同步 Issues、Pull Requests、Release 附件或 Wiki。
- 不强推、不删除 Gitee 分支或标签。若两端存在分叉提交，同步会报错，需要先人工处理。日常修改请提交到 GitHub。

## 首次授权

专用私钥已保存到本仓库的 GitHub Actions Secret：`GITEE_SSH_PRIVATE_KEY`。

在 https://gitee.com/profile/sshkeys 添加以下**个人 SSH 公钥**，标题可用 `github-actions-dushan-ai-native`。需要具有目标仓库写权限的 Gitee 账号；不要添加为仅支持读取的部署公钥。

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHU2trQkm6ez6sUkAicOPAk27+OoS57kjnf6rUNkP+Q9 github-actions-dushan-ai-native
```

个人公钥具有该账号的 Git 权限；如需限制到单个项目，可使用只拥有此仓库写权限的专用账号。

保存后，在 GitHub 的 Actions → Sync to Gitee → Run workflow 运行一次，确认成功。

## 维护

工作流固定校验 Gitee 的 SSH 主机公钥。如 Gitee 更换主机密钥，应核验后更新工作流中的公钥，不要关闭主机校验。

更换同步密钥时，同时更新 GitHub Secret 与 Gitee 个人公钥。
