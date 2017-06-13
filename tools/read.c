/*
 * @Author: mcxiaoke 
 * @Date: 2017-06-13 15:47:02 
 * @Last Modified by: mcxiaoke
 * @Last Modified time: 2017-06-13 18:23:41
 */
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/*
 * http://man7.org/linux/man-pages/man2/mmap.2.html
 * https://en.wikipedia.org/wiki/Mmap
 */

static const size_t block_size = 0x100000;
static const char *sep_kv = "∘";
static const char *sep_line = "∙";
static const char *magic = "Packer Ng Sig V2";
static const char *key = "CHANNEL";

#define handle_error(msg)   \
    do                      \
    {                       \
        perror(msg);        \
        exit(EXIT_FAILURE); \
    } while (0)

/* find the overlap array for the given pattern */
void find_overlap(const char *word, int wlen, int *ptr)
{
    int i = 2, j = 0, len = wlen;

    ptr[0] = -1;
    ptr[1] = 0;

    while (i < len)
    {
        if (word[i - 1] == word[j])
        {
            j = j + 1;
            ptr[i] = j;
            i = i + 1;
        }
        else if (j > 0)
        {
            j = ptr[j];
        }
        else
        {
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
int kmp_search(const char *str, int slen, const char *word, int wlen)
{
    int *ptr = (int *)calloc(1, sizeof(int) * (strlen(magic)));
    find_overlap(magic, strlen(magic), ptr);
    int i = 0, j = 0;

    while ((i + j) < slen)
    {
        /* match found on the target and pattern string char */
        if (word[j] == str[i + j])
        {
            if (j == (wlen - 1))
            {
                // printf("%s located at the index %d\n", word, i + 1);
                return i + 1;
            }
            j = j + 1;
        }
        else
        {
            /* manipulating next indices to compare */
            i = i + j - ptr[j];
            if (ptr[j] > -1)
            {
                j = ptr[j];
            }
            else
            {
                j = 0;
            }
        }
    }
    return -1;
}

int main(int argc, char *argv[])
{
    char *addr;
    int fd;
    struct stat sb;
    off_t offset, pa_offset;
    size_t length;
    ssize_t s;

    if (argc < 2)
    {
        fprintf(stderr, "%s file\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    fd = open(argv[1], O_RDONLY);
    if (fd == -1)
        handle_error("open");

    if (fstat(fd, &sb) == -1) /* To obtain file siclearze */
        handle_error("fstat");

    offset = sb.st_size - block_size;
    pa_offset = offset & ~(sysconf(_SC_PAGE_SIZE) - 1);
    /* offset for mmap() must be page aligned */
    length = sb.st_size - offset;
    printf("mmap file size=%zu\n", length);
    size_t pa_length = length + offset - pa_offset;
    printf("mmap real size=%zu\n", pa_length);
    printf("mmap real offset=%lld\n", pa_offset);
    addr = mmap(NULL, pa_length, PROT_READ,
                MAP_PRIVATE, fd, pa_offset);
    if (addr == MAP_FAILED)
        handle_error("mmap");

    // s = write(STDOUT_FILENO, addr + offset - pa_offset, length);
    // if (s != length)
    // {
    //     if (s == -1)
    //         handle_error("write");

    //     fprintf(stderr, "partial write");
    //     exit(EXIT_FAILURE);
    // }

    size_t index = kmp_search(addr, pa_length, magic, strlen(magic));
    printf("magic index=%zu\n", index);
    size_t li = index + strlen(magic) - 1;
    printf("magic lenindex=%zu\n", li);
    int32_t payload_len;
    memcpy(&payload_len, &addr[li], 4);
    printf("payload_len=%d\n", payload_len);
    char *payload = malloc(payload_len + 1);
    strncpy(payload, &addr[li + 4], payload_len);
    printf("payload=%s\n", payload);
    char *pos1 = strstr(payload, sep_kv);
    char *pos2 = strstr(payload, sep_line);
    size_t n1 = pos1 - payload + strlen(sep_kv);
    size_t n2 = pos2 - payload;
    size_t clen = n2 - n1;
    printf("n1=%zu, n2=%zu, clen=%zu\n", n1, n2, clen);
    char *channel = malloc(clen);
    strncpy(channel, &payload[n1], clen);
    printf("channel=%s\n", channel);
    munmap(addr, pa_length);
    close(fd);

    exit(EXIT_SUCCESS);
}