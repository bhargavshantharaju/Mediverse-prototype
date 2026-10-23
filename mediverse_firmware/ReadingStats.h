#ifndef MEDIVERSE_READING_STATS_H
#define MEDIVERSE_READING_STATS_H

struct ReadingStats {
  int median;
  int minimum;
  int maximum;
  int n;
  const char *status;
};

#endif