# 本地写作与维护

## 先区分两个目录

本仓库是 GitHub Pages 发布产物：HTML、CSS、JS 和图片。现有页面标记为 Hexo 6.3.0 生成，但仓库没有 `_config.yml`、`package.json`、`source/_posts` 或主题模板。因此不能在本仓库直接运行 `hexo new`，也不要在这里运行 `hexo init` 或用新站点覆盖旧站。

新增文章应在原来的 Hexo 源目录完成。源目录一般有：

    _config.yml
    package.json
    source/_posts/
    themes/

已检查本机部分目录及 GitHub 账号可访问仓库的当前目录，未发现完整 Hexo 写作工程；博客发布仓库 main/master 的完整提交历史中也未发现 `_config.yml`、`package.json`、`source/` 或 `themes/`。仍需要原目录位置或备份。没有源文件时，恢复写作工程是单独的迁移工作，不能把现有 HTML 当作原始 Markdown。

## 找到源目录之后的常规流程

以下命令只在原 Hexo 工程中执行，不是在当前发布仓库：

1. 按该工程的锁文件安装依赖；存在 package-lock.json 时用 `npm ci`，否则根据原工程使用的包管理器恢复依赖。
2. 用工程内安装的 Hexo 新建文章：

       npx hexo new post "我的新文章" --slug my-new-post

3. 编辑实际生成在 `source/_posts/` 内的 Markdown 文件，例如：

       ---
       title: 我的新文章
       date: 2026-10-16 18:00:00
       tags:
         - 机器人
       ---

       这里写文章摘要。

       <!-- more -->

       ## 正文

       这里写正文。

   日期是示例，按实际发布时间填写；URL 的日期结构取决于原 `_config.yml` 的 permalink 配置。

4. 图片可放入源工程的 `source/img/posts/my-new-post/`，正文用：

       ![图片说明](/img/posts/my-new-post/example.jpg)

   发布前适当缩小图片、压缩 JPEG/WebP；保留本地原图备份，不只依赖外链图床。

5. 启动原 Hexo 工程的本地预览：

       npx hexo server

   默认访问 http://localhost:4000/ 。预览后 Ctrl+C 关闭。

6. 运行 `npx hexo generate` 生成 `public/`，检查文章、首页、归档、标签页和主题功能，再按原工程确认过的部署配置发布。

不要在未检查部署配置、未备份现有发布内容时直接运行 `hexo deploy`；源工程的旧资源可能覆盖这次图片压缩和日夜模式改动。

## 日夜模式的维护

- 样式：`css/theme.css`。
- 脚本：`js/theme.js`，无第三方运行时依赖。
- 当前 71 个 HTML 页面的 `</head>` 前各引入一次：

      <link rel="stylesheet" href="/css/theme.css">
      <script src="/js/theme.js"></script>

- 脚本在页面头部恢复选择，以避免先绘制日间页面再切换；右下角按钮在 DOM 就绪后创建。
- 默认跟随系统主题；点击后用 localStorage 的 `blog-theme` 保存 `light` 或 `dark`。
- 清除这一站点的 `blog-theme` 并刷新后，恢复跟随系统。
- 不反转图片颜色；手动切换不依赖图标字体或外部 CDN。

恢复原 Hexo 源工程后，必须把这两个引用放进公共 head 模板（在原主题样式之后），把 CSS/JS 放入源工程对应的 `source/css`、`source/js` 或主题的静态资源目录。不要只改生成后的 public，否则下次构建会丢失。压缩过的背景图也要同步回源工程相应资源目录。

## 当前发布仓库的本地预览

在本仓库目录执行：

    python -m http.server 8040 --bind 127.0.0.1

访问 http://127.0.0.1:8040/ ，Ctrl+C 关闭。这只预览现有 HTML，不会生成文章。

## 主题回归检查

测试依赖 Playwright 和 Chromium，但网站本身不需要它们。本机已安装 Chromium 时可以复用，不需再次下载浏览器。

本机实际验证命令（Git Bash）：

    UV_CACHE_DIR=D:/rbr/.uv-cache uv run --no-project --index-url https://mirrors.aliyun.com/pypi/simple/ --with playwright python scripts/test_theme.py --browser D:/rbr/ms-playwright/chromium-1243/chrome-win64/chrome.exe --artifacts D:/rbr/blog-theme-check

测试会检查全部 HTML 页面、日夜切换、刷新保持、系统偏好、标签页同步、存储不可用时的降级、手机菜单和键盘操作。为避免旧 CDN 干扰，测试阻止外部网络请求；它不是旧 CDN 或文章图床的可用性测试。测试结束关闭临时浏览器与 HTTP 服务。

官方写作说明：https://hexo.io/docs/writing
官方命令说明：https://hexo.io/docs/commands
