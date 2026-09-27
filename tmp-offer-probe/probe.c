typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed long long s64;
typedef unsigned long usize;

struct mach_header_64_min {
  u32 magic; int cputype; int cpusubtype; u32 filetype;
  u32 ncmds; u32 sizeofcmds; u32 flags; u32 reserved;
};
struct load_command_min { u32 cmd; u32 cmdsize; };
struct uuid_command_min { u32 cmd; u32 cmdsize; u8 uuid[16]; };
struct timeval_min { s64 tv_sec; int tv_usec; int pad; };

extern u32 _dyld_image_count(void);
extern const void *_dyld_get_image_header(u32);
extern void _dyld_register_func_for_add_image(void (*fn)(const void *, s64));
extern void *dlsym(void *, const char *);
extern char *getenv(const char *);
extern int open(const char *, int, ...);
extern long write(int, const void *, usize);
extern int close(int);
extern int gettimeofday(struct timeval_min *, void *);

void *g_orig = 0;
extern void probe_replacement(void);

#define MH_MAGIC_64 0xfeedfacfU
#define LC_UUID 0x1bU
#define O_WRONLY 0x0001
#define O_APPEND 0x0008
#define O_CREAT  0x0200
#define RTLD_DEFAULT ((void *)(s64)-2)

static const u8 k_uuid[16] = {
  0x4c,0x4c,0x44,0x7a,0x55,0x55,0x31,0x44,
  0xa1,0xee,0xf9,0x3e,0x57,0x13,0xb7,0xd3
};
static const u8 k_fp[16] = {
  0xe5,0x03,0x1e,0xaa,0x58,0x36,0x5f,0x97,
  0xfe,0x03,0x05,0xaa,0xfd,0x7b,0x05,0xa9
};
static const u64 k_target_off = 0x44bc480ULL;
static int g_hooked = 0;

static int bytes_eq(const u8 *a, const u8 *b, usize n) {
  for (usize i=0;i<n;i++) if (a[i]!=b[i]) return 0;
  return 1;
}
static usize str_len(const char *s) {
  usize n=0; if (!s) return 0; while (s[n]) n++; return n;
}

static int make_log_path(char out[512]) {
  const char *home = getenv("HOME");
  const char *suffix = "/Documents/581_offer_probe_v1.bin";
  if (!home) {
    home = getenv("TMPDIR");
    suffix = "/581_offer_probe_v1.bin";
  }
  if (!home) return 0;
  usize a=str_len(home), b=str_len(suffix);
  if (a+b+1 >= 512) return 0;
  for (usize i=0;i<a;i++) out[i]=home[i];
  for (usize i=0;i<b;i++) out[a+i]=suffix[i];
  out[a+b]=0;
  return 1;
}

struct probe_frame {
  u64 magic;
  u32 version;
  u32 phase;
  s64 sec;
  int usec;
  u32 reserved;
  u64 regs[31];
  u64 self_fields[8];
};

static void append_frame(const struct probe_frame *f) {
  char path[512];
  if (!make_log_path(path)) return;
  int fd=open(path,O_WRONLY|O_CREAT|O_APPEND,0644);
  if (fd<0) return;
  const u8 *p=(const u8 *)f;
  usize left=sizeof(*f);
  while (left) {
    long n=write(fd,p,left);
    if (n<=0) break;
    p += (usize)n;
    left -= (usize)n;
  }
  close(fd);
}

void probe_capture(u64 *saved) {
  struct probe_frame f;
  struct timeval_min tv={0,0,0};
  gettimeofday(&tv,0);
  f.magic=0x3130425250313835ULL;
  f.version=1;
  f.phase=1;
  f.sec=tv.tv_sec;
  f.usec=tv.tv_usec;
  f.reserved=0;
  for (int i=0;i<31;i++) f.regs[i]=saved[i];
  for (int i=0;i<8;i++) f.self_fields[i]=0;
  u8 *self=(u8 *)(usize)saved[20];
  if (self) {
    for (int i=0;i<8;i++) {
      u64 v=0;
      u8 *src=self+0x10+i*8;
      u8 *dst=(u8 *)&v;
      for (int j=0;j<8;j++) dst[j]=src[j];
      f.self_fields[i]=v;
    }
  }
  append_frame(&f);
}

static void write_marker(u32 phase, u64 target) {
  struct probe_frame f;
  struct timeval_min tv={0,0,0};
  gettimeofday(&tv,0);
  f.magic=0x3130425250313835ULL;
  f.version=1; f.phase=phase;
  f.sec=tv.tv_sec; f.usec=tv.tv_usec; f.reserved=0;
  for(int i=0;i<31;i++) f.regs[i]=0;
  f.regs[0]=target;
  for(int i=0;i<8;i++) f.self_fields[i]=0;
  append_frame(&f);
}

typedef void (*MSHookFunction_t)(void *, void *, void **);

static int is_target_image(const void *header) {
  const struct mach_header_64_min *mh=(const struct mach_header_64_min *)header;
  if (!mh || mh->magic!=MH_MAGIC_64) return 0;
  const u8 *p=(const u8 *)(mh+1);
  for (u32 i=0;i<mh->ncmds;i++) {
    const struct load_command_min *lc=(const struct load_command_min *)p;
    if (lc->cmd==LC_UUID && lc->cmdsize>=24) {
      const struct uuid_command_min *uc=(const struct uuid_command_min *)p;
      return bytes_eq(uc->uuid,k_uuid,16);
    }
    if (lc->cmdsize<8) return 0;
    p += lc->cmdsize;
  }
  return 0;
}

static void try_hook(const void *header, s64 slide) {
  (void)slide;
  if (g_hooked || !is_target_image(header)) return;
  u8 *target=(u8 *)header+k_target_off;
  if (!bytes_eq(target,k_fp,16)) {
    write_marker(0xE1,(u64)(usize)target);
    return;
  }
  MSHookFunction_t hook=(MSHookFunction_t)dlsym(RTLD_DEFAULT,"MSHookFunction");
  if (!hook) {
    write_marker(0xE2,(u64)(usize)target);
    return;
  }
  hook(target,(void *)&probe_replacement,&g_orig);
  if (g_orig) {
    g_hooked=1;
    write_marker(0xA1,(u64)(usize)target);
  } else {
    write_marker(0xE3,(u64)(usize)target);
  }
}

__attribute__((constructor))
static void probe_init(void) {
  _dyld_register_func_for_add_image(try_hook);
  u32 n=_dyld_image_count();
  for (u32 i=0;i<n && !g_hooked;i++) {
    const void *h=_dyld_get_image_header(i);
    try_hook(h,0);
  }
}
