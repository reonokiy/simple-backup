import { defineConfig } from 'vitepress'

export default defineConfig({
  srcDir: "docs",
  
  title: "Simple Backup",
  description: "A simple backup tool for selfhosted services",
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Configuration', link: '/configuration' },
      { text: 'Kubernetes', link: '/kubernetes' }
    ],

    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Configuration', link: '/configuration' },
          { text: 'Compression', link: '/compression' },
          { text: 'Encryption', link: '/encryption' },
          { text: 'Scheduling', link: '/scheduling' }
        ]
      },
      {
        text: 'Deployment',
        items: [
          { text: 'Docker', link: '/docker' },
          { text: 'Kubernetes', link: '/kubernetes' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/reonokiy/simple-backup' }
    ]
  }
})
