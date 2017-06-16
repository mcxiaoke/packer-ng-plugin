/*
 * @Author: mcxiaoke
 * @Date: 2017-06-13 15:47:02
 * @Last Modified by: mcxiaoke
 * @Last Modified time: 2017-06-13 18:23:41
 */
//#include "config.h"
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

/*
 * http://man7.org/linux/man-pages/man2/mmap.2.html
 * https://en.wikipedia.org/wiki/Mmap
 */

static const char *apk_ext = ".apk";
static const off_t block_size = 0x100000;
static const char *sep_kv = "∘";
static const char *sep_line = "∙";
static const char *magic = "Packer Ng Sig V2";
// static const char *key = "CHANNEL";
// static const char *version = "v2.0.0";

#define handle_error(msg)                                                      \
  do {                                                                         \
    printf(msg);                                                               \
    exit(EXIT_FAILURE);                                                        \
  } while (0)

#define handle_not_found()                                                     \
  do {                                                                         \
    printf("Channel not found\n");                                             \
    exit(EXIT_FAILURE);                                                        \
  } while (0)

/* find the overlap array for the given pattern */
void find_overlap(const char *word, size_t wlen, int *ptr) {
  size_t i = 2, j = 0, len = wlen;
  ptr[0] = -1;
  ptr[1] = 0;

  while (i < len) {
    if (word[i - 1] == word[j]) {
      j = j + 1;
      ptr[i] = j;
      i = i + 1;
    } else if (j > 0) {
      j = ptr[j];
    } else {
      ptr[i] = 0;
      i = i + 1;
    }
  }
  return;
}

/*
* finds the position of the pattern in the given target string
* target - str, patter - word
*/
int32_t kmp_search(const char *str, int slen, const char *word, int wlen) {
  //   printf("kmp_search() slen=%zu, wlen=%zu\n", slen, wlen);
  int *ptr = (int *)calloc(1, sizeof(int) * (strlen(magic)));
  find_overlap(magic, strlen(magic), ptr);
  int32_t i = 0, j = 0;

  while ((i + j) < slen) {
    /* match found on the target and pattern string char */
    if (word[j] == str[i + j]) {
      if (j == (wlen - 1)) {
        return i + 1;
      }
      j = j + 1;
    } else {
      /* manipulating next indices to compare */
      i = i + j - ptr[j];
      if (ptr[j] > -1) {
        j = ptr[j];
      } else {
        j = 0;
      }
    }
  }
  return -1;
}

int str_has_suffix(const char *str, const char *suf) {
  const char *a = str + strlen(str);
  const char *b = suf + strlen(suf);
  while (a != str && b != suf) {
    if (*--a != *--b)
      break;
  }
  return b == suf && *a == *b;
}

// ensure write '\0' at end
// http://en.cppreference.com/w/c/string/byte/strncpy
char *strncpy_2(char *dest, const char *src, size_t count) {
  char *ret = strncpy(dest, src, count);
  dest[count] = '\0';
  return ret;
}

int main(int argc, char *argv[]) {
  char *addr;
  int fd;
  struct stat sb;
  off_t offset, pa_offset;
  size_t length;

  if (argc < 2) {
    // printf("Version: %d.%d.%d\n", VER_MAJOR, VER_MINOR, VER_PATCH);
    printf("Usage: %s app.apk    (show apk channel)\n", argv[0]);
    exit(EXIT_FAILURE);
  }
  char *fn = argv[1];
  // printf("file name: %s\n", fn);
  if (!str_has_suffix(fn, apk_ext)) {
    handle_error("Not apk file\n");
  }
  fd = open(fn, O_RDONLY);
  if (fd == -1) {
    handle_error("No such file\n");
  }
  if (fstat(fd, &sb) == -1) {
    handle_error("Can not read");
  }
  // printf("file mode=%d\n", sb.st_mode);
  if (!S_ISREG(sb.st_mode)) {
    handle_error("Not regular file\n");
  }
  if (sb.st_size < block_size) {
    offset = 0;
  } else {
    offset = sb.st_size - block_size;
  }
  pa_offset = offset & ~(sysconf(_SC_PAGE_SIZE) - 1);
  /* offset for mmap() must be page aligned */
  length = sb.st_size - offset;
  // printf("mmap file size=%zu\n", length);
  size_t pa_length = length + offset - pa_offset;
  // printf("mmap real size=%zu\n", pa_length);
  // printf("mmap real offset=%lld\n", pa_offset);
  addr = mmap(NULL, pa_length, PROT_READ, MAP_PRIVATE, fd, pa_offset);
  if (addr == MAP_FAILED) {
    handle_error("Can not mmap\n");
  }

  int32_t index = kmp_search(addr, pa_length, magic, strlen(magic));
  if (index == -1) {
    handle_not_found();
  }
  //   printf("magic index=%d\n", index);
  int32_t li = index + strlen(magic) - 1;
  //   printf("magic lenindex=%d\n", li);
  int32_t payload_len;
  memcpy(&payload_len, &addr[li], 4);
  //   printf("payload_len=%d\n", payload_len);
  if (payload_len < 0 || payload_len > block_size) {
    handle_not_found();
  }
  // char *payload = malloc(payload_len + 1);
  char payload[payload_len + 1];
  strncpy_2(payload, &addr[li + 4], payload_len);
  // payload[payload_len] = '\0';
  //   printf("payload=%s\n", payload);
  char *pos_start = strstr(payload, sep_kv);
  char *pos_end = strstr(payload, sep_line);
  if (pos_start == NULL || pos_end == NULL) {
    handle_not_found();
  }
  size_t c_start = pos_start - payload + strlen(sep_kv);
  size_t c_end = pos_end - payload;
  size_t c_len = c_end - c_start;
  // printf("c_start=%zu, c_end=%zu, clen=%zu\n", c_start, c_end, clen);
  // char *channel = malloc(clen + 1);
  char channel[c_len + 1];
  strncpy_2(channel, &payload[c_start], c_len);
  // channel[c_len] = '\0';
  printf("%s\n", channel);
  // free(payload);
  // free(channel);
  munmap(addr, pa_length);
  close(fd);
  exit(EXIT_SUCCESS);
}