# Compression

## Overview

The backup program supports multiple compression formats. By default, it uses Zstandard (`tar.zst`) compression, which offers the best balance of compression ratio and speed.

## Supported Formats

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| `tar.zst` | `.tar.zst` | **Default**. Zstandard compression via Python 3.14 built-in | Best overall choice: fast and high compression |
| `tar.gz` | `.tar.gz` | Gzip compression | Wide compatibility, good balance |
| `tar.bz2` | `.tar.bz2` | Bzip2 compression | Higher compression, slower |
| `tar.xz` | `.tar.xz` | LZMA compression | Highest compression, slowest |
| `tar` | `.tar` | Uncompressed archive | Fast, no compression overhead |
| `zip` | `.zip` | ZIP archive with deflate | Cross-platform compatibility |
| `gzip` | `.gz` | Gzip single file | For single file backups only |
| `none` | N/A | No compression or archiving | Backup individual files as-is |

## Setting Compression Format

Use the `BACKUP_COMPRESSION` environment variable:

```bash
export BACKUP_COMPRESSION=tar.zst  # Default
python main.py
```

## Format Details

### Zstandard (tar.zst) - Recommended

```bash
export BACKUP_COMPRESSION=tar.zst
```

**Advantages:**
- Excellent compression ratio (similar to bzip2)
- Very fast compression and decompression
- Built into Python 3.14+ (no external dependencies)
- Modern, actively developed

**Best for:** Most use cases, especially large backups

### Gzip (tar.gz)

```bash
export BACKUP_COMPRESSION=tar.gz
```

**Advantages:**
- Universal compatibility
- Good balance of speed and compression
- Standard on Unix systems

**Best for:** Maximum compatibility

### Bzip2 (tar.bz2)

```bash
export BACKUP_COMPRESSION=tar.bz2
```

**Advantages:**
- Better compression than gzip
- Widely supported

**Best for:** When file size is more important than speed

### LZMA/XZ (tar.xz)

```bash
export BACKUP_COMPRESSION=tar.xz
```

**Advantages:**
- Highest compression ratio
- Good for long-term archival

**Best for:** Maximum compression, infrequent access

### Uncompressed Tar

```bash
export BACKUP_COMPRESSION=tar
```

**Advantages:**
- Fast backup and restore
- Preserves directory structure
- No CPU overhead

**Best for:** Fast local backups, pre-compressed data

### ZIP

```bash
export BACKUP_COMPRESSION=zip
```

**Advantages:**
- Cross-platform (Windows, Mac, Linux)
- Individual file access without full extraction

**Best for:** Windows compatibility, heterogeneous environments

### Gzip Single File

```bash
export BACKUP_COMPRESSION=gzip
```

**Limitations:**
- Only works for single file backups
- Raises error if source is a directory

**Best for:** Compressing individual large files

### No Compression

```bash
export BACKUP_COMPRESSION=none
```

**Behavior:**
- Backs up files individually without archiving
- Preserves directory structure on destination
- Uses OpenDAL for both reading and writing

**Best for:** 
- Incremental backups
- Already compressed data
- Need to access individual files remotely

## Compression Comparison

Based on typical mixed data (documents, code, configs):

| Format | Relative Speed | Relative Size | CPU Usage |
|--------|---------------|---------------|-----------|
| none | ⚡⚡⚡⚡⚡ Fastest | 💾💾💾💾💾 Largest | ▁ Minimal |
| tar | ⚡⚡⚡⚡⚡ Fastest | 💾💾💾💾💾 Largest | ▁ Minimal |
| tar.zst | ⚡⚡⚡⚡ Very Fast | 💾💾 Small | ▃ Low |
| tar.gz | ⚡⚡⚡ Fast | 💾💾💾 Medium | ▄ Medium |
| zip | ⚡⚡⚡ Fast | 💾💾💾 Medium | ▄ Medium |
| tar.bz2 | ⚡⚡ Moderate | 💾💾 Small | ▆ High |
| tar.xz | ⚡ Slow | 💾 Smallest | ▇ Very High |

## Recommendations

### For Daily Backups
```bash
export BACKUP_COMPRESSION=tar.zst
```
Fast, efficient, modern default.

### For Long-Term Archives
```bash
export BACKUP_COMPRESSION=tar.xz
```
Maximum compression for storage savings.

### For Maximum Compatibility
```bash
export BACKUP_COMPRESSION=zip
```
Works everywhere, easy to extract.

### For Incremental/Sync-Style Backups
```bash
export BACKUP_COMPRESSION=none
```
Backup files individually for selective restore.

## Custom Archive Names

When using compression (any format except `none`), you can specify a custom archive name:

```bash
export BACKUP_ARCHIVE_NAME=myproject_backup
export BACKUP_COMPRESSION=tar.zst
```

This creates: `myproject_backup.tar.zst`

If not specified, the default format is:
```
backup_{source_dirname}_{timestamp}.{extension}
```

Example: `backup_documents_20250109_143022.tar.zst`
