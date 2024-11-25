<div align="center">
    <img src="https://pbs.twimg.com/profile_banners/1828170456110682112/1725545674/1500x500" alt="Gurubase Image" /><br/>
</div>


<div align="center">

[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/9CMRSQPqx6)
[![Twitter](https://img.shields.io/badge/Twitter-%231DA1F2.svg?style=for-the-badge&logo=x&logoColor=white)](https://twitter.com/gurubaseio)
[![Mastodon](https://img.shields.io/badge/Mastodon-%236364FF.svg?style=for-the-badge&logo=mastodon&logoColor=white)](https://mastodon.social/@gurubaseio)
[![Bluesky](https://img.shields.io/badge/Bluesky-%230285FF.svg?style=for-the-badge&logo=bluesky&logoColor=white)](https://bsky.app/profile/gurubase.bsky.social)

</div>

# Gurubase

- [What is Gurubase](#what-is-gurubase)
- [How to Create a Guru](#how-to-create-a-guru)
- [How to Claim a Guru](#how-to-claim-a-guru)
- [Showcase Your Guru](#showcase-your-guru)
- [How to Update Datasources](#how-to-update-datasources)
- [License](#license)
- [Help](#help)
- [Used By](#used-by)

## What is Gurubase

[Gurubase](https://gurubase.io) is a centralized RAG-based learning and troubleshooting assistant platform. Each "Guru" has its own custom knowledge base (such as the latest documentation, PDFs, YouTube videos, etc.) to generate answers for user queries. It is not a coding assistant like GitHub Copilot or similar tools.

## How to Create a Guru

Currently, only the Gurubase team can create a Guru. Please open an issue on this repository with the title "Guru Creation Request" and include the GitHub repository link in the issue content. We prioritize Guru creation requests from the maintainers of the tools. Please mention whether you are the maintainer of the tool. If you are not the maintainer, it would be helpful to obtain the maintainer's permission before opening a creation request for the tool.

## How to Claim a Guru

Although you can't create a Guru, you can manage it on Gurubase. For example, you can add, remove, or reindex the datasources. To claim a Guru, you must have a Gurubase account and be one of the tool's maintainers. Please open an issue with the title "Guru Claim Request". Include the link to the Guru (e.g., `https://gurubase.io/g/anteon`), your Gurubase username, and a link proving you are one of the maintainers of the tool, such as a PR merged by you.

## Showcase Your Guru

### Badge

Like hundreds of GitHub repositories, you can add a badge to your README to guide your users to learn about your tool on Gurubase.

[Example Badge:](https://github.com/opencost/opencost)
```
[![Gurubase](https://img.shields.io/badge/Gurubase-Ask%20OpenCost%20Guru-006BFF)](https://gurubase.io/g/opencost)
```

<img src="imgs/badge_sample.png" alt="Gurubase Image" width="500"/><br/>

### Widget

You can also add an "Ask AI" widget to your documentation by importing a [small JS script](https://github.com/getanteon/guru-widget).

<img src="imgs/widget_sample.png" alt="Gurubase Image" width="500"/><br/>

## How to Update Datasources

Datasources can include your tool's documentation webpages, YouTube videos, or PDF files. You can add new ones, remove existing ones, or reindex them. Reindexing ensures your Guru is updated based on changes to the indexed datasources. For example, if you update your tool's documentation, you can reindex those pages so your Guru generates answers based on the latest data.

Once you claim your Guru, you will see your Gurus in the "My Gurus" section.

<img src="imgs/image.png" alt="Gurubase Image" width="300"/><br/>

Click the Guru you want to update. On the edit page, click "Reindex" for the datasource you want to reindex.

<img src="imgs/image-1.png" alt="Gurubase Image" width="720"/><br/>

You can also see the "Last Index Date" on the URL pages.

<img src="imgs/image-2.png" alt="Gurubase Image" width="720"/><br/>

## License

All the content generated by Gurubase aligns with the license of the datasources used to generate answers. More details can be found on the [Terms of Usage](https://gurubase.io/terms-of-use) page, Section 2.

## Help

We prefer Discord for written communication. [Join our channel!](https://discord.gg/9CMRSQPqx6) To stay updated on new features, you can follow us on [X](https://x.com/gurubaseio), [Mastodon](https://mastodon.social/@gurubaseio), and [Bluesky](https://bsky.app/profile/gurubase.bsky.social).

## Used By

Gurubase currently hosts **hundreds** of Gurus, and it grows every day. Here are some repositories that showcase their Gurus in their READMEs or documentation.

<table>
<tr>
<td align="center">
  <a href="https://github.com/openimsdk/open-im-server">
    <img src="https://avatars.githubusercontent.com/u/84842645?s=48&v=4" width="40" height="40">
    <br>
    <b>Open IM</b>
    <br>
    14.1K ★
  </a>
</td>

<td  align="center">
  <a href="https://github.com/vanna-ai/vanna">
    <img src="https://avatars.githubusercontent.com/u/132533812?s=48&v=4" width="40" height="40">
    <br>
    <b>Vanna</b>
    <br>
    12K ★
  </a>
</td>


<td align="center">
  <a href="https://github.com/duplicati/duplicati">
    <img src="https://avatars.githubusercontent.com/u/8270231?s=48&v=4" width="40" height="40">
    <br>
    <b>Duplicati</b>
    <br>
    11.2K ★
  </a>
</td>

<td  align="center">
  <a href="https://github.com/Nozbe/WatermelonDB">
    <img src="https://gurubase.io/_next/image?url=https%3A%2F%2Fs3.eu-central-1.amazonaws.com%2Fanteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x%2Fwatermelon_logo_83e295693d.png&w=96&q=75" width="40" height="40">
    <br>
    <b>WatermelonDB</b>
    <br>
    10.6K ★
  </a>
</td>

<td  align="center">
  <a href="https://github.com/gorse-io/gorse">
    <img src="https://avatars.githubusercontent.com/u/74893108?s=48&v=4" width="40" height="40">
    <br>
    <b>Gorse</b>
    <br>
    8.6K ★
  </a>
</td>

<td align="center">
  <a href="https://github.com/sqlfluff/sqlfluff">
    <img src="https://avatars.githubusercontent.com/u/71874918?s=48&v=4" width="40" height="40">
    <br>
    <b>SQLFluff</b>
    <br>
    8K ★
  </a>
</td>

<td align="center">
  <a href="https://github.com/ast-grep/ast-grep">
    <img src="https://avatars.githubusercontent.com/u/114017360?s=48&v=4" width="40" height="40">
    <br>
    <b>ast-grep(sg)</b>
    <br>
    7.6K ★
  </a>
</td>


<td  align="center">
  <i>100+ more</i>
</td>
</tr>
</table>