#define _GNU_SOURCE
#include <sys/socket.h>
#include <linux/if_alg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

static uint8_t key[16], iv[16], plain[4096], sw[4096], hw[4096], recovered[4096];
static void timed_out(int sig) { (void)sig; _exit(124); }
static void die(const char *where) { perror(where); exit(1); }
static void hex(const char *s, uint8_t *b, size_t n) {
    unsigned int x;
    for (size_t i=0;i<n;i++) { if (sscanf(s+2*i,"%2x",&x)!=1) exit(2); b[i]=x; }
}
static void alg_crypt(const char *name, unsigned int op, const uint8_t *in, uint8_t *out, size_t n, int has_iv) {
    int fd=-1, child=-1;
    struct sockaddr_alg sa={ .salg_family=AF_ALG };
    struct iovec iov={ .iov_base=(void *)in, .iov_len=n };
    char control[CMSG_SPACE(sizeof(uint32_t))+CMSG_SPACE(sizeof(struct af_alg_iv)+16)]={0};
    struct msghdr msg={ .msg_iov=&iov, .msg_iovlen=1, .msg_control=control };
    struct cmsghdr *cm;
    strncpy((char *)sa.salg_type,"skcipher",sizeof(sa.salg_type)-1);
    strncpy((char *)sa.salg_name,name,sizeof(sa.salg_name)-1);
    alarm(5);
    if ((fd=socket(AF_ALG,SOCK_SEQPACKET,0))<0) die("socket");
    if (bind(fd,(struct sockaddr *)&sa,sizeof(sa))) die(name);
    if (setsockopt(fd,SOL_ALG,ALG_SET_KEY,key,sizeof(key))) die("key");
    if ((child=accept(fd,NULL,NULL))<0) die("accept");
    msg.msg_controllen=CMSG_SPACE(sizeof(uint32_t));
    if (has_iv) msg.msg_controllen+=CMSG_SPACE(sizeof(struct af_alg_iv)+16);
    cm=CMSG_FIRSTHDR(&msg); cm->cmsg_level=SOL_ALG; cm->cmsg_type=ALG_SET_OP;
    cm->cmsg_len=CMSG_LEN(sizeof(uint32_t)); memcpy(CMSG_DATA(cm),&op,sizeof(op));
    if (has_iv) {
        cm=CMSG_NXTHDR(&msg,cm); cm->cmsg_level=SOL_ALG; cm->cmsg_type=ALG_SET_IV;
        cm->cmsg_len=CMSG_LEN(sizeof(struct af_alg_iv)+16);
        struct af_alg_iv *v=(void *)CMSG_DATA(cm); v->ivlen=16; memcpy(v->iv,iv,16);
    }
    if (sendmsg(child,&msg,0)!=(ssize_t)n) die("sendmsg");
    if (read(child,out,n)!=(ssize_t)n) die("read");
    close(child); close(fd); alarm(0);
}
static double seconds(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec/1e9; }
int main(int argc,char **argv) {
    const char *suffix=(argc>1 && !strcmp(argv[1],"hardware"))?"eip93":"generic";
    const char *modes[]={"ecb","cbc","ctr"};
    const char *answers[]={"3ad77bb40d7a3660a89ecaf32466ef97","7649abac8119b246cee98e9b12e9197d","874d6191b620e3261bef6864990db6ce"};
    char name[64], generic[64]; uint8_t expected[16];
    signal(SIGALRM,timed_out); setvbuf(stdout,NULL,_IOLBF,0);
    hex("2b7e151628aed2a6abf7158809cf4f3c",key,16);
    for (int m=0;m<3;m++) {
        snprintf(name,sizeof(name),"%s(aes-%s)",modes[m],suffix);
        snprintf(generic,sizeof(generic),"%s(aes-generic)",modes[m]);
        hex("6bc1bee22e409f96e93d7e117393172a",plain,16);
        hex(m==2?"f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff":"000102030405060708090a0b0c0d0e0f",iv,16);
        hex(answers[m],expected,16);
        alg_crypt(name,ALG_OP_ENCRYPT,plain,hw,16,m!=0);
        if (memcmp(hw,expected,16)) { fprintf(stderr,"NIST mismatch %s\n",name); return 3; }
        alg_crypt(name,ALG_OP_DECRYPT,hw,recovered,16,m!=0);
        if (memcmp(recovered,plain,16)) return 4;
        for (size_t i=0;i<sizeof(plain);i++) plain[i]=(uint8_t)(i*7+11);
        for (size_t n=1024;n<=4096;n*=2) {
            alg_crypt(generic,ALG_OP_ENCRYPT,plain,sw,n,m!=0);
            alg_crypt(name,ALG_OP_ENCRYPT,plain,hw,n,m!=0);
            if (memcmp(sw,hw,n)) { fprintf(stderr,"large mismatch %s %zu\n",name,n); return 5; }
            alg_crypt(name,ALG_OP_DECRYPT,hw,recovered,n,m!=0);
            if (memcmp(recovered,plain,n)) return 6;
        }
        printf("PASS %s NIST vector, encrypt/decrypt, 1024/2048/4096-byte software comparison\n",name);
        double start=seconds();
        for (int i=0;i<128;i++) alg_crypt(name,ALG_OP_ENCRYPT,plain,hw,4096,m!=0);
        double duration=seconds()-start;
        printf("BENCH %s %.3f MB/s (includes AF_ALG setup/copy overhead)\n",name,128.0*4096/duration/1000000);
    }
    puts("ALL_AES_CHECKS_PASS"); return 0;
}
