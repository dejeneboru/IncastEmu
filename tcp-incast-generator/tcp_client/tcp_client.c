#include "tcp_client.h"
#include "sys/sendfile.h"
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/time.h>
#include <netinet/tcp.h>
#include <pthread.h>
#include <math.h>

#define MAX_READ 1000000

/* Temprorarily... manually set the onset point for experiments.
 * It could be automatically calculated by knowing the block size and
 * the base of slow start window size instead.*/
#define ONSET 20
#define BETA 0.1

// prototypes
void *listen_connection(void *ptr);

int num_dest;
int *dest_port;
int *src_port;
char (*dest_addr)[20];
uint req_size;
uint req_size_n;
int iter;
int *sockets;            
pthread_t *threads;
int *indexes;
struct timeval *start_time;
struct timeval *stop_time; 
int *fmax_usec;
int *fmin_usec;
int *favg_usec; 

int histogram[4];    

typedef struct header {
    int index;
    int delay;
} Header;

double getStdDev(int avg, int x[], int len) {
    double var = 0;
    for (int i = 0; i < len; i++) {
        var += pow(x[i] - avg , 2);
    }
    var /= len;
    return sqrt(var);

}

int main (int argc, char *argv[]) {
    FILE *fd;
    FILE *outfd;
    int ret;
    //int max_sec;
    int max_usec;
    //int min_sec;
    int min_usec;
    //int avg_sec;
    int avg_usec;
    //double avg_msec;
    int numSent;
    int sock_opt = 1;
    // used for calculate the avg, stddev for n iterations
    int* usec_list;

    for (int i = 0; i < 4; i++)
        histogram[i] = 0;

    if (argv[1] == NULL) {
        printf("Missing input file...\n");
        exit(-1);
    }

    if (argv[2] == NULL) {
        printf("Missing output csv file name...\n");
        exit(-1);
    }

    printf("Reading file: %s\n", argv[1]);
    fd = fopen(argv[1], "r");

    outfd = fopen(argv[2], "w");

    if (fd == NULL) {
        perror("Unable to open input file");
        exit(-1);
    }

    if (outfd == NULL) {
        perror("Unable to open output csv file");
        exit(-1);
    }

    fscanf (fd, "destinations %d\n", &num_dest);
    printf("Number of destinations: %d\n", num_dest);

    dest_addr = malloc(num_dest * sizeof(char[20]));
    dest_port = malloc(num_dest * sizeof(int));
    src_port = malloc(num_dest * sizeof(int));
    sockets = malloc(num_dest * sizeof(int));
    threads = malloc(num_dest * sizeof(pthread_t));
    indexes = malloc(num_dest * sizeof(int));
    stop_time = malloc(num_dest * sizeof(struct timeval));
    start_time = malloc(num_dest * sizeof(struct timeval));
    fmax_usec = malloc(num_dest * sizeof(int));
    fmin_usec = malloc(num_dest * sizeof(int));
    favg_usec = malloc(num_dest * sizeof(int));

    for (int i = 0; i < num_dest; i++) {
        int tmp;
        fscanf(fd, "%d dest %s %d %d\n", &tmp, dest_addr[i], &dest_port[i], &src_port[i]);
        printf("%d - Dest: %s, %d - Src: %d\n", tmp, dest_addr[i], dest_port[i], src_port[i]);
    }

    fscanf(fd, "size %u\n", &req_size);
    printf("Request size: %u\n", req_size);
    //req_size = req_size / num_dest;
    //printf("Request size on each server: %u\n", req_size);
    req_size_n = htonl(req_size);

    fscanf(fd, "iterations %d\n", &iter);
    printf("Iterations: %d\n", iter);
    usec_list = malloc(iter * sizeof(int));

    fclose(fd);


    for (int i = 0; i < num_dest; i++) {
        struct sockaddr_in servaddr;
        int sock;
        sock = socket(AF_INET, SOCK_STREAM, 0);

        setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &sock_opt, sizeof(sock_opt));
        // 20K for TCP rcvbuf
        int rcbf = 20 * 1024;
        int sdbf = 20 * 1024;
        setsockopt(listenfd, IPPROTO_TCP, SO_RCVBUF, &rcbf, sizeof(rcbf));
        setsockopt(listenfd, IPPROTO_TCP, SO_SNDBUF, &sdbf, sizeof(sdbf));

        int quickack;
        socklen_t quickack_len;

        getsockopt(sock, IPPROTO_TCP, TCP_QUICKACK, &quickack, &quickack_len);
        printf("Quick ACK: %d\n", quickack);
        quickack = 1;
        setsockopt(sock, IPPROTO_TCP, TCP_QUICKACK, &quickack, sizeof(quickack));

        //int rcvbuf = 100 * 1024;
        // setsockopt(sock, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));

        if (src_port[i] > 0) {
            memset(&servaddr, 0, sizeof(servaddr));
            servaddr.sin_family = AF_INET;
            servaddr.sin_addr.s_addr = htonl(INADDR_ANY);
            servaddr.sin_port = htons(src_port[i]);
            bind(sock, (struct sockaddr *) &servaddr, sizeof(servaddr));
        }      

        memset(&servaddr, 0, sizeof(servaddr));
        servaddr.sin_family = AF_INET;
        servaddr.sin_port = htons(dest_port[i]);
        inet_pton(AF_INET, dest_addr[i], &servaddr.sin_addr);
        ret = connect(sock, (struct sockaddr *) &servaddr, sizeof(servaddr));

        if (ret < 0) {
            char err_msg[100];
            sprintf(err_msg, "Unable to connect %s:%d", dest_addr[i], dest_port[i]);
            perror(err_msg);
            sockets[i] = -1;
            exit(-1);
        }
        else {
            printf("Connected to %s:%d\n", dest_addr[i], dest_port[i]);
            sockets[i] = sock;
        }
        indexes[i] = i;

        fmax_usec[i] = 0;
        fmin_usec[i] = 999999999;
        favg_usec[i] = 0;
    }

    max_usec = 0;
    min_usec = 999999999;
    avg_usec = 0;
    numSent = 0;

    // start iterating iter iterations of requests to servers
    for (int i = 0; i < iter; i++) {
        struct timeval tstart;
        int usec;
        int sec;

        gettimeofday(&tstart, NULL);

        // create threads for receiving files
        for (int j = 0; j < num_dest; j++) {
            /* client-side delays*/
            /*
            if (num_dest > 4) {
                struct timespec tim, tim2;
                tim.tv_sec = 0;
                tim.tv_nsec = 1000000;

                if(nanosleep(&tim , &tim2) < 0 )   
                {
                    printf("Nano sleep system call failed \n");
                    return -1;
                }
            }
            */
            Header* hp = (Header*)malloc(sizeof(Header));
            hp->index = indexes[j];
            hp->delay = htonl(0);
            if (j > ONSET) {
                // num_dest * 1ms -> approximately the transfer time
                hp->delay = htonl(num_dest * (1 + BETA)); // 1ms RTT * num_dest
            }
            //pthread_create(&threads[j], NULL, listen_connection, (void *) &indexes[j]);
            pthread_create(&threads[j], NULL, listen_connection, (void *) hp);
        }

        // wait for transfers to complete
        for (int j = 0; j < num_dest; j++) {
            pthread_join(threads[j], NULL);
        }

        struct timeval *tv = &stop_time[0];
        struct timeval *ts = &start_time[0];
        /*Request completion time across servers*/
        for (int j = 1; j < num_dest; j++) {
            if (ts->tv_sec > start_time[j].tv_sec || (ts->tv_sec == start_time[j].tv_sec && ts->tv_usec > start_time[j].tv_usec)) {
                ts = &start_time[j];
            }
        }
        for (int j = 1; j < num_dest; j++) {
            if (tv->tv_sec < stop_time[j].tv_sec || (tv->tv_sec == stop_time[j].tv_sec && tv->tv_usec < stop_time[j].tv_usec)) {
                tv = &stop_time[j];
            }
        }
        sec = tv->tv_sec - ts->tv_sec;
        usec = tv->tv_usec - ts->tv_usec;

        usec += sec * 1000000;
        sec = 0;

        usec_list[i] = usec;

        numSent++;
        if (usec < min_usec)
            min_usec = usec;
        if (usec > max_usec)
            max_usec = usec;

        avg_usec += usec;

        for (int j = 0; j < num_dest; j++) {
            sec = stop_time[j].tv_sec - start_time[j].tv_sec;
            usec = stop_time[j].tv_usec - start_time[j].tv_usec;

            usec += sec * 1000000;

            if (usec < fmin_usec[j])
                fmin_usec[j] = usec;
            if (usec > fmax_usec[j])
                fmax_usec[j] = usec;
            favg_usec[j] += usec;
        }
        fprintf(outfd, "%d,%d\n", i, usec);
    }
    printf("\n");
    fclose(outfd);

    // close connections
    for (int i = 0; i < num_dest; i++) {
        close(sockets[i]);
    }

    if (numSent > 0) {
        
        avg_usec = avg_usec / numSent;

        for (int i = 0; i < num_dest; i++) {
            double ftotal_usec = favg_usec[i];
            favg_usec[i] = favg_usec[i] / numSent;
            double conn_sent = req_size * numSent / (1024.0 * 1024.0);
            printf("Connection: %d\nAvg: %.3f msec\nMin: %.3f msec\nMax: %.3f msec\nGoodput: %.3f Mbps\n",
                    i, favg_usec[i] / 1000.0, fmin_usec[i] / 1000.0, fmax_usec[i] / 1000.0, 8.0 * conn_sent / (ftotal_usec / 1000000.0));
        }
        printf("Overall\nAvg: %.3f msec\nMin: %.3f msec\nMax: %.3f msec\n",
                avg_usec / 1000.0, min_usec / 1000.0, max_usec / 1000.0);

        double totalsent = ((double)req_size * num_dest * numSent) / (1024.0 * 1024.0);

        printf("Total sent: %.2f MB\n", totalsent);
        double total_sec = (avg_usec * numSent) / 1000000.0;
        printf("Total duration: %.4f sec\n", total_sec);

        printf("Overall Goodput: %.3f Mbps\n", 8 * totalsent / total_sec);


        // calculate the standard deviation
        double stddev = getStdDev(avg_usec, usec_list, iter);
        printf ("avg_usec + 3 * stddev = %f\n", avg_usec + 3 * stddev);
        printf ("avg_usec + 2 * stddev = %f\n", avg_usec + 2 * stddev);
        printf ("avg_usec + 1 * stddev = %f\n", avg_usec + 1 * stddev);
        printf ("avg_usec = %f\n", (double)avg_usec);
        for (int i = 0; i < numSent; i++) {
            if (usec_list[i] > avg_usec + 2 * stddev) 
                histogram[3]++;
            else if (usec_list[i] > avg_usec + 1 * stddev) 
                histogram[2]++;
            else if (usec_list[i] > avg_usec) 
                histogram[1]++;
            else 
                histogram[0]++;
        }
        
        printf("\nHistogram\n");
        for (int i = 0; i < 4; i++) {
            printf("%d - %d\n", i, histogram[i]);
        }
    }

    free(stop_time);
    free(start_time);
    free(dest_port);
    free(src_port);
    free(dest_addr);
    free(indexes);
    free(sockets);
    free(threads);
    free(fmax_usec);
    free(fmin_usec);
    free(favg_usec);
    free(usec_list);

    return 0;
    }

void *listen_connection(void *ptr) {
    Header hp = *((Header *)ptr);
    int index = hp.index;
    int delay = hp.delay;
    int sock = sockets[index];
    int total = 0;
    int n;
    char buf[MAX_READ];

    memcpy(buf, &delay, sizeof(int));
    memcpy(buf + sizeof(int), &req_size_n, sizeof(uint));

    gettimeofday(&start_time[index], NULL);
    write(sockets[index], buf, sizeof(int) + sizeof(uint));

    do {
        n = read(sock, buf, MAX_READ);
        int quickack = 1;
        setsockopt(sock, IPPROTO_TCP, TCP_QUICKACK, &quickack, sizeof(quickack));

        if (n > 0) {
            total += n;
            //printf("n: %d, total: %d \n", n, total);
        }

    } while (total < req_size && n > 0);

    if (total == 0) {
        printf(" Error: server closed the connection. Probably requested file not found on the server\n");
        exit(-1);
    }
    else if (total != req_size) {
        printf(" Error: file transfer incomplete!\n");
        exit(-1);
    }
    gettimeofday(&stop_time[index], NULL);

    //printf("Finished! index: %d\n", index);

    return 0;
}

